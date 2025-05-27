FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir google-auth google-auth-oauthlib google-auth-httplib2 \
    gunicorn firebase-admin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/output /tmp/data

# Set environment variables
ENV PORT=8080
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/service-account.json"

# Start the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 'cloud_main:create_app()'
