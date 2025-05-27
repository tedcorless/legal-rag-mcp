"""
Main application for Legal RAG Application with Model Context Protocol.
This module integrates all components and provides the main entry point.
"""

import os
import sys
import logging
import argparse
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

# Import components
from src.db.schema import init_db, get_session
from src.mcp.server import MCPServer
from src.google_drive.client import GoogleDriveClient
from src.document_processing.processor import DocumentProcessor
from src.rag.engine import RAGEngine
from src.output.pdf_generator import PDFGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("legal_rag_mcp.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LegalRAGApplication:
    """
    Main application class that integrates all components of the Legal RAG system.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Legal RAG application.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize components
        self._init_components()
        
        logger.info("Legal RAG Application initialized")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "db": {
                "url": "sqlite:///legal_rag.db"
            },
            "mcp_server": {
                "host": "0.0.0.0",
                "port": 5000
            },
            "google_drive": {
                "credentials_path": "credentials.json",
                "root_folder": "Legal Documents"
            },
            "document_processing": {
                "ocr_enabled": True,
                "chunk_size": 1000,
                "chunk_overlap": 200
            },
            "rag": {
                "model_name": "all-MiniLM-L6-v2",
                "index_path": "data/faiss_index",
                "chunk_data_path": "data/chunks.json"
            },
            "output": {
                "output_dir": "output"
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                
                # Merge user config with defaults
                for section, settings in user_config.items():
                    if section in default_config:
                        default_config[section].update(settings)
                    else:
                        default_config[section] = settings
                
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
        
        return default_config
    
    def _init_components(self):
        """Initialize all application components."""
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Initialize database
        db_url = self.config["db"]["url"]
        self.db_engine = init_db(db_url)
        self.db_session = get_session(self.db_engine)
        logger.info(f"Database initialized: {db_url}")
        
        # Initialize MCP server
        self.mcp_server = MCPServer()
        logger.info("MCP server initialized")
        
        # Initialize Google Drive client
        credentials_path = self.config["google_drive"]["credentials_path"]
        self.drive_client = GoogleDriveClient(credentials_path=credentials_path if os.path.exists(credentials_path) else None)
        logger.info("Google Drive client initialized")
        
        # Initialize document processor
        doc_config = self.config["document_processing"]
        self.doc_processor = DocumentProcessor(
            ocr_enabled=doc_config["ocr_enabled"],
            chunk_size=doc_config["chunk_size"],
            chunk_overlap=doc_config["chunk_overlap"]
        )
        logger.info("Document processor initialized")
        
        # Initialize RAG engine
        rag_config = self.config["rag"]
        self.rag_engine = RAGEngine(
            model_name=rag_config["model_name"],
            index_path=rag_config["index_path"] if os.path.exists(rag_config["index_path"]) else None,
            chunk_data_path=rag_config["chunk_data_path"] if os.path.exists(rag_config["chunk_data_path"]) else None
        )
        logger.info("RAG engine initialized")
        
        # Initialize PDF generator
        output_dir = self.config["output"]["output_dir"]
        os.makedirs(output_dir, exist_ok=True)
        self.pdf_generator = PDFGenerator(output_dir=output_dir)
        logger.info("PDF generator initialized")
    
    def process_document(self, file_path: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a document and add it to the system.
        
        Args:
            file_path: Path to the document file
            document_type: Optional document type override
            
        Returns:
            Processing result information
        """
        logger.info(f"Processing document: {file_path}")
        
        # Process document
        doc_result = self.doc_processor.process_document(file_path)
        
        # Override document type if provided
        if document_type:
            doc_result["document_type"] = document_type
        
        # Upload to Google Drive
        drive_folder = None
        drive_id = None
        
        if self.drive_client.service:
            try:
                # Use document type for folder organization
                drive_id = self.drive_client.upload_file(
                    file_path=file_path,
                    document_type=doc_result["document_type"]
                )
                logger.info(f"Uploaded document to Google Drive: {drive_id}")
            except Exception as e:
                logger.error(f"Error uploading to Google Drive: {str(e)}")
        
        # Add to RAG engine
        if doc_result["chunks"]:
            document_id = os.path.basename(file_path)
            self.rag_engine.add_document(document_id, doc_result["chunks"])
            logger.info(f"Added document to RAG engine: {document_id} ({len(doc_result['chunks'])} chunks)")
        
        # Save RAG index and data
        rag_config = self.config["rag"]
        self.rag_engine.save(rag_config["index_path"], rag_config["chunk_data_path"])
        
        return {
            "file_path": file_path,
            "document_type": doc_result["document_type"],
            "metadata": doc_result["metadata"],
            "google_drive_id": drive_id,
            "chunks_count": len(doc_result["chunks"]),
            "processed_at": datetime.now().isoformat()
        }
    
    def search_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents using the RAG engine.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        logger.info(f"Searching documents: {query}")
        return self.rag_engine.search(query, top_k=top_k)
    
    def generate_case_report(self, case_data: Dict[str, Any]) -> str:
        """
        Generate a case report PDF.
        
        Args:
            case_data: Case information
            
        Returns:
            Path to the generated PDF
        """
        logger.info(f"Generating case report for: {case_data.get('title', 'Untitled Case')}")
        return self.pdf_generator.generate_case_report(case_data)
    
    def generate_assessment_notice(self, assessment_data: Dict[str, Any]) -> str:
        """
        Generate an assessment notice PDF.
        
        Args:
            assessment_data: Assessment information
            
        Returns:
            Path to the generated PDF
        """
        logger.info(f"Generating assessment notice for: {assessment_data.get('owner', {}).get('name', 'Unknown Owner')}")
        return self.pdf_generator.generate_assessment_notice(assessment_data)
    
    def setup_google_drive_folders(self) -> Dict[str, str]:
        """
        Set up the Google Drive folder structure for legal documents.
        
        Returns:
            Dictionary mapping folder names to folder IDs
        """
        if not self.drive_client.service:
            logger.warning("Google Drive client not initialized, cannot set up folders")
            return {}
        
        root_folder = self.config["google_drive"]["root_folder"]
        logger.info(f"Setting up Google Drive folders with root: {root_folder}")
        
        # Create custom folder structure based on user preferences
        folder_ids = {}
        
        # Create root folder
        root_id = self.drive_client._find_or_create_folder(root_folder)
        folder_ids[root_folder] = root_id
        
        # Create user-preferred folder structure
        custom_folders = [
            "inbound communications from the client",
            "our data we create",
            "that which is sent out"
        ]
        
        for folder_name in custom_folders:
            folder_id = self.drive_client.create_folder(folder_name, parent_id=root_id)
            folder_ids[folder_name] = folder_id
        
        logger.info(f"Created {len(folder_ids)} folders in Google Drive")
        return folder_ids
    
    def run_mcp_server(self):
        """Run the MCP server."""
        host = self.config["mcp_server"]["host"]
        port = self.config["mcp_server"]["port"]
        logger.info(f"Starting MCP server on {host}:{port}")
        self.mcp_server.run(host=host, port=port)
    
    def close(self):
        """Close all resources."""
        if hasattr(self, 'db_session'):
            self.db_session.close()
        logger.info("Legal RAG Application resources closed")


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description='Legal RAG Application with Model Context Protocol')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--process', help='Process a document file')
    parser.add_argument('--search', help='Search for documents')
    parser.add_argument('--setup-drive', action='store_true', help='Set up Google Drive folders')
    parser.add_argument('--run-server', action='store_true', help='Run the MCP server')
    
    args = parser.parse_args()
    
    # Initialize application
    app = LegalRAGApplication(config_path=args.config)
    
    try:
        if args.process:
            # Process a document
            result = app.process_document(args.process)
            print(json.dumps(result, indent=2))
        
        elif args.search:
            # Search for documents
            results = app.search_documents(args.search)
            print(json.dumps(results, indent=2))
        
        elif args.setup_drive:
            # Set up Google Drive folders
            folder_ids = app.setup_google_drive_folders()
            print(json.dumps(folder_ids, indent=2))
        
        elif args.run_server:
            # Run the MCP server
            app.run_mcp_server()
        
        else:
            # No specific command, print help
            parser.print_help()
    
    finally:
        # Clean up resources
        app.close()


if __name__ == "__main__":
    main()
