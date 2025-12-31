#!/bin/bash
set -e

PROJECT_ID="hk-bus-eta-482904"
REGION="asia-east2"

# Add local gcloud to PATH if it exists
export PATH="$PWD/google-cloud-sdk/bin:$PATH"

echo "Deploying to Project: $PROJECT_ID"

# 1. Set Project
gcloud config set project $PROJECT_ID

# 2. Build Container (Increase timeout for large upload)
echo "Building container (this may take a while for 1.3GB data)..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/bus-travel-time --timeout=20m

# 3. Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy bus-travel-time \
  --image gcr.io/$PROJECT_ID/bus-travel-time \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi

# 4. Deploy Hosting
echo "Deploying Hosting..."
firebase deploy --only hosting --project $PROJECT_ID

echo "Deployment Complete!"
