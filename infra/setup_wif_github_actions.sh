#!/usr/bin/env bash
# Sets up Workload Identity Federation so GitHub Actions can deploy to Cloud Run
# WITHOUT a downloaded service-account key. Restricts trust to one specific GitHub
# repository.
#
# Usage: bash infra/setup_wif_github_actions.sh PROJECT_ID github-owner/github-repo
#
# Examples:
#   bash infra/setup_wif_github_actions.sh agenticaigcplearn abhimasum/GoogleCloudAi
#   bash infra/setup_wif_github_actions.sh my-adk-lab myusername/my-fork
#
# This script creates:
# - A service account for GitHub Actions deployment
# - A Workload Identity Pool and Provider
# - IAM policies that restrict deployment to THIS specific repository only

set -euo pipefail

PROJECT_ID="${1:?Usage: setup_wif_github_actions.sh PROJECT_ID github-owner/github-repo}"
GITHUB_REPO="${2:?Usage: setup_wif_github_actions.sh PROJECT_ID github-owner/github-repo}"

POOL_ID="github-pool"
PROVIDER_ID="github-provider"
SA_NAME="github-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "GitHub Actions Workload Identity Federation Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Configuration:"
echo "  Project ID:       ${PROJECT_ID}"
echo "  GitHub Repo:      ${GITHUB_REPO}"
echo "  Service Account:  ${SA_EMAIL}"
echo ""
echo "This setup creates a SECURE, KEYLESS authentication method for GitHub Actions."
echo "No service account JSON keys are created or stored in your repository."
echo ""

echo "==> Creating deploy service account: ${SA_EMAIL}"
if gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
  echo "   ✓ Service account already exists"
else
  gcloud iam service-accounts create "${SA_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="GitHub Actions deployer"
  echo "   ✓ Service account created"
fi

echo ""
echo "==> Granting service account permissions..."
echo "   Roles:"
echo "     • roles/run.admin (deploy to Cloud Run)"
echo "     • roles/artifactregistry.writer (push Docker images)"
echo "     • roles/iam.serviceAccountUser (use service accounts)"
echo "     • roles/cloudscheduler.admin (manage Cloud Scheduler jobs)"
echo "     • roles/storage.objectViewer (read from Cloud Storage)"
echo "     • roles/aiplatform.user (use Vertex AI)"
echo ""

for ROLE in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser \
            roles/cloudscheduler.admin roles/storage.objectViewer roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None \
    >/dev/null 2>&1 || true
done
echo "   ✓ Roles granted"

echo ""
echo "==> Creating Workload Identity Pool: ${POOL_ID}"
if gcloud iam workload-identity-pools describe "${POOL_ID}" --project="${PROJECT_ID}" --location="global" >/dev/null 2>&1; then
  echo "   ✓ Pool already exists"
else
  gcloud iam workload-identity-pools create "${POOL_ID}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --display-name="GitHub Actions pool"
  echo "   ✓ Pool created"
fi

echo ""
echo "==> Creating Workload Identity Provider: ${PROVIDER_ID}"
echo "   Restricting trust to ONLY: ${GITHUB_REPO}"
if gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" --location="global" --workload-identity-pool="${POOL_ID}" >/dev/null 2>&1; then
  echo "   ✓ Provider already exists"
else
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --workload-identity-pool="${POOL_ID}" \
    --display-name="GitHub provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
    --issuer-uri="https://token.actions.githubusercontent.com"
  echo "   ✓ Provider created"
fi

echo ""
echo "==> Configuring IAM trust policy"
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_REPO}" \
  >/dev/null 2>&1 || true
echo "   ✓ Trust policy configured (only ${GITHUB_REPO} can use this service account)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Setup Complete - Add these to GitHub repository variables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 How to add repository variables:"
echo ""
echo "1. Go to: https://github.com/${GITHUB_REPO}/settings/variables/actions"
echo "2. Click 'New repository variable' for each value below"
echo "3. Copy EXACTLY (including projects/... prefix)"
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ Name: GCP_WORKLOAD_IDENTITY_PROVIDER                        │"
echo "│ Value:                                                      │"
echo "│ projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ Name: GCP_SERVICE_ACCOUNT                                   │"
echo "│ Value: ${SA_EMAIL}                                   │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "📋 Also add these repository variables (from Step 4 in docs/SETUP.md):"
echo ""
echo "  GCP_PROJECT_ID       = ${PROJECT_ID}"
echo "  GCP_REGION           = europe-west4  (or your chosen region)"
echo "  RAG_CORPUS           = projects/.../ragCorpora/...  (from ingest.py output)"
echo "  RAG_CORPUS_ID        = 4611686018427387904  (numeric ID)"
echo "  GCS_BUCKET           = ${PROJECT_ID}-adk-docs"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Add both values above to GitHub repository variables"
echo "2. Add RAG_CORPUS values from ingestion step"
echo "3. Push to main branch: git push"
echo "4. GitHub Actions will automatically build & deploy your agents"
echo "5. Watch: https://github.com/${GITHUB_REPO}/actions"
echo ""
