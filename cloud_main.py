"""
Google Cloud adapted main application for Legal RAG Application with Model Context Protocol.
This module provides Cloud-specific integration and serves as the entry point for Cloud Run.
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from google.cloud import storage, firestore
import google.oauth2.credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Import application components
from src.mcp.server import MCPServer
from src.rag.engine import RAGEngine
from src.document_processing.processor import DocumentProcessor
from src.output.pdf_generator import PDFGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application for Google Cloud."""
    # Load configuration
    config = {}
    if os.path.exists('google_config.json'):
        with open('google_config.json', 'r') as f:
            config = json.load(f)
    
    # Initialize Flask app
    app = Flask(__name__)
    
    # Initialize Firestore client
    db = firestore.Client()
    
    # Initialize Storage client
    storage_client = storage.Client()
    
    # Initialize MCP server
    mcp_server = MCPServer()
    
    # Initialize document processor
    doc_processor = DocumentProcessor(
        ocr_enabled=True,
        chunk_size=1000,
        chunk_overlap=200
    )
    
    # Initialize RAG engine
    rag_engine = RAGEngine(
        model_name="all-MiniLM-L6-v2"
    )
    
    # Initialize PDF generator
    pdf_generator = PDFGenerator(output_dir="/tmp/output")
    
    # Register MCP routes with Flask app
    for rule in mcp_server.app.url_map.iter_rules():
        endpoint = rule.endpoint
        view_func = mcp_server.app.view_functions[endpoint]
        app.add_url_rule(rule.rule, endpoint, view_func, methods=rule.methods)
    
    # Add health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}
    
    # Add document processing endpoint
    @app.route('/api/process-document', methods=['POST'])
    def process_document():
        """Process a document uploaded to Cloud Storage."""
        data = request.json
        
        if not data or 'bucket' not in data or 'file' not in data:
            return jsonify({'error': 'Missing bucket or file parameter'}), 400
        
        bucket_name = data['bucket']
        file_name = data['file']
        document_type = data.get('document_type')
        
        try:
            # Download file from Cloud Storage
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(file_name)
            temp_file_path = f"/tmp/{os.path.basename(file_name)}"
            blob.download_to_filename(temp_file_path)
            
            # Process document
            doc_result = doc_processor.process_document(temp_file_path)
            
            # Override document type if provided
            if document_type:
                doc_result["document_type"] = document_type
            
            # Store document metadata in Firestore
            doc_ref = db.collection('documents').document()
            doc_ref.set({
                'file_name': file_name,
                'bucket': bucket_name,
                'document_type': doc_result["document_type"],
                'metadata': doc_result["metadata"],
                'processed_at': firestore.SERVER_TIMESTAMP
            })
            
            # Add to RAG engine
            if doc_result["chunks"]:
                document_id = doc_ref.id
                rag_engine.add_document(document_id, doc_result["chunks"])
                
                # Store chunks in Firestore
                for chunk in doc_result["chunks"]:
                    db.collection('document_chunks').add({
                        'document_id': document_id,
                        'chunk_index': chunk["index"],
                        'content': chunk["content"],
                        'metadata': {
                            'start_char': chunk.get("start_char"),
                            'end_char': chunk.get("end_char")
                        }
                    })
            
            # Clean up temporary file
            os.remove(temp_file_path)
            
            return jsonify({
                'document_id': doc_ref.id,
                'document_type': doc_result["document_type"],
                'chunks_count': len(doc_result["chunks"])
            })
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # Add search endpoint
    @app.route('/api/search', methods=['POST'])
    def search():
        """Search for documents using the RAG engine."""
        data = request.json
        
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query parameter'}), 400
        
        query = data['query']
        top_k = data.get('top_k', 5)
        
        try:
            results = rag_engine.search(query, top_k=top_k)
            return jsonify({'results': results})
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # Add PDF generation endpoint
    @app.route('/api/generate-case-report', methods=['POST'])
    def generate_case_report():
        """Generate a case report PDF."""
        data = request.json
        
        if not data:
            return jsonify({'error': 'Missing case data'}), 400
        
        try:
            output_file = pdf_generator.generate_case_report(data)
            
            # Upload PDF to Cloud Storage
            bucket_name = config.get('storage', {}).get('documents_bucket', 'legal-rag-documents')
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(f"reports/{os.path.basename(output_file)}")
            blob.upload_from_filename(output_file)
            
            # Make the blob publicly accessible
            blob.make_public()
            
            return jsonify({
                'pdf_url': blob.public_url,
                'file_name': os.path.basename(output_file)
            })
        except Exception as e:
            logger.error(f"Error generating case report: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # Add Google Drive setup endpoint
    @app.route('/api/setup-drive', methods=['POST'])
    def setup_drive():
        """Set up Google Drive folder structure."""
        data = request.json
        credentials_json = data.get('credentials')
        
        if not credentials_json:
            return jsonify({'error': 'Missing credentials'}), 400
        
        try:
            # Save credentials temporarily
            temp_creds_path = '/tmp/credentials.json'
            with open(temp_creds_path, 'w') as f:
                json.dump(credentials_json, f)
            
            # Initialize Google Drive client
            from src.google_drive.client import GoogleDriveClient
            drive_client = GoogleDriveClient(credentials_path=temp_creds_path)
            
            # Create custom folder structure based on user preferences
            folder_ids = {}
            
            # Create root folder
            root_folder = config.get('drive', {}).get('root_folder', 'Legal Documents')
            root_id = drive_client._find_or_create_folder(root_folder)
            folder_ids[root_folder] = root_id
            
            # Create user-preferred folder structure
            custom_folders = [
                "inbound communications from the client",
                "our data we create",
                "that which is sent out"
            ]
            
            for folder_name in custom_folders:
                folder_id = drive_client.create_folder(folder_name, parent_id=root_id)
                folder_ids[folder_name] = folder_id
            
            # Clean up temporary credentials
            os.remove(temp_creds_path)
            
            return jsonify({'folder_ids': folder_ids})
        except Exception as e:
            logger.error(f"Error setting up Google Drive: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
