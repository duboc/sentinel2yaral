#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Check if GCP_PROJECT is set
if [ -z "$GCP_PROJECT" ]; then
    echo "Error: GCP_PROJECT not set in .env file"
    exit 1
fi

# Deploy directly to Cloud Run from source
echo "Deploying to Cloud Run with GCP_PROJECT=$GCP_PROJECT"

gcloud run deploy sentinel2yaral \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT=$GCP_PROJECT" 