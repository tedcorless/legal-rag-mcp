# Legal RAG Application with Model Context Protocol - User Guide

## Overview
This document provides instructions for using the Legal RAG (Retrieval-Augmented Generation) application built with Model Context Protocol. The system is designed for small law firms (fewer than 10 lawyers) that handle condominium and homeowners association cases under Florida Chapters 718 and 720.

## System Requirements
- Python 3.8 or higher
- Google account for Drive integration
- Internet connection for model access

## Installation

1. Extract the `legal_rag_mcp.zip` file to your desired location
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up Google Drive API credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Drive API
   - Create OAuth 2.0 credentials
   - Download the credentials JSON file and save it as `credentials.json` in the project root directory

## Configuration
The application can be configured by creating a `config.json` file in the project root directory. Example configuration:

```json
{
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
    "ocr_enabled": true,
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
```

## Usage

### Setting Up Google Drive Folders
To set up the Google Drive folder structure:

```
python main.py --setup-drive
```

This will create the following folder structure:
- Legal Documents (root)
  - inbound communications from the client
  - our data we create
  - that which is sent out

### Processing Documents
To process a legal document:

```
python main.py --process /path/to/document.pdf
```

The system will:
1. Extract text and metadata from the document
2. Classify the document type
3. Upload it to the appropriate Google Drive folder
4. Add it to the RAG engine for retrieval

### Searching Documents
To search for information across processed documents:

```
python main.py --search "assessment collection procedure"
```

### Running the MCP Server
To start the Model Context Protocol server:

```
python main.py --run-server
```

The server will be available at http://localhost:5000 by default.

## Key Features

### Automatic Document Organization
The system automatically classifies and organizes legal documents based on their content, storing them in the appropriate Google Drive folders according to your preferred structure.

### Document Processing
- Supports multiple file formats (PDF, DOCX, TXT, images)
- OCR for scanned documents
- Automatic metadata extraction
- Document chunking for efficient retrieval

### Legal-Specific Features
- Assessment collection workflow following FL Chapter 718 and 720
- Notice generation for assessment collection
- Timeline tracking for legal deadlines
- Citation and reference management

### Report Generation
- Case report generation
- Assessment notice creation
- Legal timeline visualization
- Professional legal document formatting

## Troubleshooting

### Google Drive Integration Issues
If you encounter issues with Google Drive integration:
1. Verify that your credentials.json file is valid and has the correct permissions
2. Ensure you have completed the OAuth flow when prompted
3. Check that you have sufficient storage space in your Google Drive

### Document Processing Issues
If document processing fails:
1. Verify that the file format is supported
2. Check if OCR is enabled for image-based documents
3. Ensure the file is not corrupted or password-protected

## Support
For additional support or questions, please refer to the documentation in the `architecture.md` and `implementation_plan.md` files.
