# Google Cloud Project Setup for Legal RAG Application

## Project Configuration
- Project Name: legal-rag-mcp
- Region: us-central1 (closest to Boulder, Colorado)
- Authentication: IAM-based access
- Database: Google Cloud Firestore

## Required APIs
- Cloud Build API
- Cloud Run API
- Google Drive API
- Firestore API
- Cloud Storage API
- Secret Manager API
- Identity and Access Management (IAM) API

## Resource Setup
- Cloud Storage buckets for document storage and RAG indexes
- Firestore database for document metadata and application data
- IAM roles and permissions for secure access
- Cloud Run service for application hosting

## Deployment Steps
1. Create new Google Cloud project
2. Enable required APIs
3. Set up IAM roles and permissions
4. Create Cloud Storage buckets
5. Initialize Firestore database
6. Configure Google Drive integration
7. Deploy application to Cloud Run

## Configuration Files
- google_config.json - Google Cloud specific configuration
- Dockerfile - Container configuration for Cloud Run
- cloud_main.py - Cloud-adapted application entry point
- cloudbuild.yaml - Deployment configuration

## Access Control
- IAM-based access control for application
- Service account for Google Drive integration
- OAuth flow for initial setup
