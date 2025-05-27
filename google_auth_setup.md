# Google Cloud Authentication and Google Drive Configuration

## IAM Authentication Setup

### Service Account Creation
```bash
# Create service account for the application
gcloud iam service-accounts create legal-rag-app \
  --display-name="Legal RAG Application Service Account"

# Get the service account email
SERVICE_ACCOUNT=$(gcloud iam service-accounts list \
  --filter="displayName:Legal RAG Application Service Account" \
  --format="value(email)")

# Grant necessary roles to the service account
gcloud projects add-iam-policy-binding legal-rag-mcp \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding legal-rag-mcp \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding legal-rag-mcp \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

### User Access Configuration
```bash
# Grant access to specific users (replace with actual email)
gcloud projects add-iam-policy-binding legal-rag-mcp \
  --member="user:your-email@example.com" \
  --role="roles/run.invoker"

# Create a custom role for application users
gcloud iam roles create LegalRagUser \
  --project=legal-rag-mcp \
  --title="Legal RAG User" \
  --description="Role for Legal RAG application users" \
  --permissions="run.services.get"

# Assign the custom role to users
gcloud projects add-iam-policy-binding legal-rag-mcp \
  --member="user:your-email@example.com" \
  --role="projects/legal-rag-mcp/roles/LegalRagUser"
```

## Google Drive Integration

### OAuth Configuration
1. Go to the Google Cloud Console: https://console.cloud.google.com/
2. Navigate to "APIs & Services" > "Credentials"
3. Click "Create Credentials" > "OAuth client ID"
4. Select "Web application" as the application type
5. Add authorized redirect URIs:
   - `https://legal-rag-mcp-[unique-id].run.app/oauth2callback`
   - `http://localhost:8080/oauth2callback` (for local testing)
6. Download the credentials JSON file

### Google Drive API Setup
```bash
# Enable the Google Drive API
gcloud services enable drive.googleapis.com

# Create a secret for storing OAuth credentials
gcloud secrets create drive-credentials \
  --replication-policy="automatic"

# Store the OAuth credentials in Secret Manager
gcloud secrets versions add drive-credentials \
  --data-file="/path/to/downloaded/credentials.json"

# Grant the service account access to the secret
gcloud secrets add-iam-policy-binding drive-credentials \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

### Google Drive Authentication Flow

The application will use a two-step authentication process:

1. **Initial Setup (Admin)**:
   - Admin authenticates with Google using OAuth
   - Application stores refresh token in Secret Manager
   - Admin sets up initial folder structure

2. **Ongoing Operation (Service Account)**:
   - Application uses stored refresh token to obtain access tokens
   - Service account performs operations on behalf of the authenticated user
   - No user interaction required for routine operations

## Configuration File

Create a `google_config.json` file with the following structure:

```json
{
  "project_id": "legal-rag-mcp",
  "region": "us-central1",
  "service_account": "legal-rag-app@legal-rag-mcp.iam.gserviceaccount.com",
  "storage": {
    "documents_bucket": "legal-rag-documents",
    "indexes_bucket": "legal-rag-indexes"
  },
  "firestore": {
    "collection_prefix": "legal_rag_"
  },
  "drive": {
    "credentials_secret": "drive-credentials",
    "root_folder": "Legal Documents"
  },
  "auth": {
    "require_iam": true,
    "allowed_roles": [
      "roles/run.invoker",
      "projects/legal-rag-mcp/roles/LegalRagUser"
    ]
  }
}
```

## Dockerfile Update

Update the Dockerfile to include authentication handling:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir google-auth google-auth-oauthlib google-auth-httplib2

COPY . .

# Set environment variables
ENV PORT=8080
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/service-account.json"

# Start the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 'cloud_main:create_app()'
```

## Cloud Run Deployment with Authentication

```bash
# Deploy to Cloud Run with IAM authentication
gcloud run deploy legal-rag-mcp \
  --image=gcr.io/legal-rag-mcp/legal-rag-mcp \
  --region=us-central1 \
  --platform=managed \
  --service-account=$SERVICE_ACCOUNT \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=legal-rag-mcp" \
  --no-allow-unauthenticated
```

## Testing Authentication

To test the authentication setup:

```bash
# Get the Cloud Run URL
SERVICE_URL=$(gcloud run services describe legal-rag-mcp \
  --region=us-central1 \
  --format="value(status.url)")

# Test with authentication
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" $SERVICE_URL/health
```

## Troubleshooting

If you encounter authentication issues:

1. Verify IAM roles are correctly assigned
2. Check that the service account has the necessary permissions
3. Ensure OAuth credentials are correctly configured
4. Verify the Secret Manager contains the correct credentials
5. Check Cloud Run logs for authentication errors
