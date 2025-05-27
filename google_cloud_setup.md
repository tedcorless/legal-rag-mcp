# Google Cloud Setup for Legal RAG Application

## Overview
This document provides instructions for deploying the Legal RAG application with Model Context Protocol in a Google Cloud environment. This setup leverages Google Cloud services for hosting, storage, and authentication.

## Google Cloud Services Used
- Google Cloud Run - For hosting the application
- Google Cloud Storage - For storing document data and indexes
- Google Drive API - For document organization and storage
- Google Cloud Firestore - For database (alternative to SQLite)
- Google Cloud IAM - For authentication and access control

## Prerequisites
- Google Cloud account
- Google Cloud SDK installed locally
- Project owner or editor permissions

## Setup Steps

### 1. Create a Google Cloud Project
```bash
# Create a new Google Cloud project
gcloud projects create legal-rag-mcp --name="Legal RAG MCP"

# Set the project as the current active project
gcloud config set project legal-rag-mcp
```

### 2. Enable Required APIs
```bash
# Enable required Google Cloud APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudrun.googleapis.com
gcloud services enable drive.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 3. Set Up Google Drive API
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Create OAuth 2.0 Client ID credentials
4. Download the credentials JSON file
5. Store the credentials securely

### 4. Create Cloud Storage Buckets
```bash
# Create buckets for document storage and RAG indexes
gcloud storage buckets create gs://legal-rag-documents
gcloud storage buckets create gs://legal-rag-indexes
```

### 5. Set Up Firestore Database
```bash
# Create Firestore database in Native mode
gcloud firestore databases create --region=us-east1
```

### 6. Adapt Application Configuration
Create a `google_config.json` file with the following structure:
```json
{
  "project_id": "legal-rag-mcp",
  "storage": {
    "documents_bucket": "legal-rag-documents",
    "indexes_bucket": "legal-rag-indexes"
  },
  "firestore": {
    "collection_prefix": "legal_rag_"
  },
  "drive": {
    "credentials_path": "credentials.json",
    "root_folder": "Legal Documents"
  },
  "mcp_server": {
    "host": "0.0.0.0",
    "port": 8080
  }
}
```

### 7. Create Dockerfile
Create a `Dockerfile` in the project root:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 'cloud_main:create_app()'
```

### 8. Create Cloud-Specific Main File
Create `cloud_main.py` with Google Cloud adaptations:
```python
import os
import json
from flask import Flask
from google.cloud import storage, firestore
from src.mcp.server import MCPServer

def create_app():
    # Load configuration
    config = {}
    if os.path.exists('google_config.json'):
        with open('google_config.json', 'r') as f:
            config = json.load(f)
    
    # Initialize Flask app
    app = Flask(__name__)
    
    # Initialize MCP server
    mcp_server = MCPServer()
    
    # Register MCP routes with Flask app
    for rule in mcp_server.app.url_map.iter_rules():
        endpoint = rule.endpoint
        view_func = mcp_server.app.view_functions[endpoint]
        app.add_url_rule(rule.rule, endpoint, view_func, methods=rule.methods)
    
    # Add health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
```

### 9. Create Cloud Build Configuration
Create `cloudbuild.yaml`:
```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/legal-rag-mcp', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/legal-rag-mcp']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'legal-rag-mcp'
      - '--image=gcr.io/$PROJECT_ID/legal-rag-mcp'
      - '--region=us-east1'
      - '--platform=managed'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/legal-rag-mcp'
```

### 10. Deploy to Google Cloud
```bash
# Build and deploy using Cloud Build
gcloud builds submit --config=cloudbuild.yaml
```

### 11. Set Up Google Drive Integration
1. The first time the application runs, it will prompt for OAuth authentication
2. Follow the authentication flow to grant the application access to Google Drive
3. The application will create the folder structure in Google Drive

## Accessing the Application
After deployment, the application will be available at the Cloud Run URL provided in the deployment output. You can also find this URL in the Google Cloud Console under Cloud Run.

## Monitoring and Maintenance
- View logs in Google Cloud Console under Cloud Run > legal-rag-mcp > Logs
- Monitor storage usage in Google Cloud Storage
- Check Firestore database for document metadata and user data

## Security Considerations
- The deployment uses public access for demonstration purposes
- For production, configure authentication using Google Cloud IAM
- Consider setting up VPC Service Controls for additional security
- Implement proper access controls for Google Drive folders
