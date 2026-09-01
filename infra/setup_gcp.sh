#!/usr/bin/env bash
# One-time project setup: enables required APIs, creates the Cloud Storage bucket for
# source documents, an Artifact Registry repo for container images, and a dedicated
# service account Cloud Scheduler will use to invoke the ingestion Cloud Run service.
#
# Usage: bash infra/setup_gcp.sh PROJECT_ID [REGION]
# 
# Examples:
#   bash infra/setup_gcp.sh agenticaigcplearn europe-west4
#   bash infra/setup_gcp.sh my-adk-lab us-west1
#
# Supported regions for RAG Engine: europe-west4, us-west1, asia-southeast1
# (us-central1 is restricted for new projects - use europe-west4 instead)

set -euo pipefail

PROJECT_ID="${1:?Usage: setup_gcp.sh PROJECT_ID [REGION]}"
REGION="${2:-europe-west4}"  # Default to europe-west4 (supports RAG Engine for new projects)
BUCKET="gs://${PROJECT_ID}-adk-docs"
AR_REPO="adk-agents"
SCHEDULER_SA="scheduler-invoker"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Google Cloud AI Project Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Configuration:"
echo "  Project ID: ${PROJECT_ID}"
echo "  Region:     ${REGION}"
echo "  Bucket:     ${BUCKET}"
echo ""

# Validate region choice
if [[ "${REGION}" == "us-central1" ]]; then
  echo "⚠️  WARNING: us-central1 RAG Engine is restricted for new projects."
  echo "   Please use: europe-west4, us-west1, or asia-southeast1 instead."
  echo "   Proceeding anyway, but RAG corpus creation may fail."
  echo ""
fi

echo "==> Setting active project to ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}"

echo ""
echo "==> Enabling required APIs (this can take 1-2 minutes)..."
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com
echo "   ✓ APIs enabled"

echo ""
echo "==> Creating Cloud Storage bucket ${BUCKET}"
if gsutil ls -b "${BUCKET}" >/dev/null 2>&1; then
  echo "   ✓ Bucket already exists"
else
  gsutil mb -l "${REGION}" "${BUCKET}"
  echo "   ✓ Bucket created in ${REGION}"
fi

echo ""
echo "==> Creating Artifact Registry repo '${AR_REPO}' in ${REGION}"
if gcloud artifacts repositories describe "${AR_REPO}" --location="${REGION}" >/dev/null 2>&1; then
  echo "   ✓ Repository already exists"
else
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Container images for the ADK sample agents"
  echo "   ✓ Repository created"
fi

echo ""
echo "==> Creating Cloud Scheduler service account"
if gcloud iam service-accounts describe "${SCHEDULER_SA}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1; then
  echo "   ✓ Service account already exists"
else
  gcloud iam service-accounts create "${SCHEDULER_SA}" \
    --display-name="Cloud Scheduler invoker for the ingestion service"
  echo "   ✓ Service account created"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Setup Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Resources created:"
echo ""
echo "  📦 Cloud Storage Bucket:"
echo "     ${BUCKET}"
echo ""
echo "  🐳 Artifact Registry (Docker):"
echo "     ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"
echo ""
echo "  👤 Service Account:"
echo "     ${SCHEDULER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Upload sample documents:"
echo "   gsutil -m cp data/sample_docs/*.md ${BUCKET}/"
echo ""
echo "2. Create RAG corpus and ingest documents (Step 4 in docs/SETUP.md):"
echo "   cd ingestion && python ingest.py"
echo ""
echo "3. Copy your RAG_CORPUS_ID value from the ingestion output and save it"
echo ""
echo "For more info, see: docs/SETUP.md"
echo ""
