# Deployment Guide

This guide explains how to deploy and manage the multi-agent system on Google Cloud Platform.

## 🚀 Quick Deploy

### Option 1: Automatic Deploy (Push to Master)

Any push to the `master` branch that changes agent code automatically triggers deployment:

```bash
git add -A
git commit -m "Your changes"
git push origin master
```

The workflow will:
1. ✅ Clean up old resources (old images, stopped services)
2. ✅ Setup BigQuery dataset with sample data
3. ✅ Deploy retriever agent (RAG specialist)
4. ✅ Deploy orchestrator agent (with embedded BigQuery agent)
5. ✅ Deploy ingestion service
6. ✅ Upload documents to GCS
7. ✅ Trigger immediate corpus ingestion

### Option 2: Manual Deploy (GitHub Actions UI)

1. Go to: https://github.com/abhimasum/GoogleCloudAi/actions
2. Select "Deploy ADK agents" workflow
3. Click "Run workflow"
4. Choose options:
   - **cleanup_before_deploy**: `true` to delete old services first (recommended)
5. Click "Run workflow"

## 🧹 Cleanup Resources

To save costs when not using the system:

### Via GitHub Actions UI

1. Go to: https://github.com/abhimasum/GoogleCloudAi/actions
2. Select "🧹 Cleanup Resources" workflow
3. Click "Run workflow"
4. Configure what to delete:
   - **delete_storage**: Delete GCS bucket contents (`true`/`false`)
   - **delete_docker_images**: Delete old Docker images (`true`/`false`)
   - **delete_rag_corpus**: Delete RAG knowledge base (`true`/`false`) ⚠️
5. Click "Run workflow"

**⚠️ Important:** Deleting the RAG corpus requires re-ingesting all documents on next deploy (takes ~5-10 minutes).

### Via Command Line

```bash
# Trigger cleanup with all options
gh workflow run cleanup.yml \
  -f delete_storage=true \
  -f delete_docker_images=true \
  -f delete_rag_corpus=false
```

## 📋 What Gets Deployed

### Cloud Run Services (3 total)

1. **retriever-agent**
   - RAG specialist using Vertex AI RAG Engine
   - Exposes A2A protocol for agent-to-agent calls
   - URL: `https://retriever-agent-<hash>-ew.a.run.app`

2. **orchestrator-agent** 
   - Main entry point with web UI
   - Embeds BigQuery agent locally (cost-efficient)
   - Delegates to retriever via A2A protocol
   - URL: `https://orchestrator-agent-<hash>-ew.a.run.app`

3. **ingestion**
   - Updates RAG corpus from GCS bucket
   - Runs on schedule (daily at 3 AM)
   - Can be triggered manually
   - Private service (no unauthenticated access)

### BigQuery Dataset

- **Dataset**: `geography_index` (europe-west4)
- **Tables**:
  - `countries` (1 row: India)
  - `states` (5 rows: Maharashtra, Karnataka, Tamil Nadu, Uttar Pradesh, West Bengal)
  - `districts` (7 rows: Mumbai, Pune, Nagpur, Bengaluru, Mysuru, Chennai, Coimbatore)

### Cloud Storage

- **Bucket**: `gs://agenticaigcplearn-adk-docs`
- **Contents**: Markdown documents from `data/sample_docs/`

### Artifact Registry

- **Repository**: `adk-agents` (europe-west4)
- **Images**: 
  - `retriever-agent:latest`
  - `orchestrator-agent:latest`
  - `ingestion:latest`

## 🔄 Deployment Workflow Details

### Phase 1: Cleanup (Optional)

Runs automatically on push or when manually enabled:

```yaml
cleanup-old-resources:
  - Delete old Cloud Run services (will be recreated)
  - Clean up old Docker images (keep last 3 versions)
```

### Phase 2: BigQuery Setup

```yaml
setup-bigquery:
  - Install BigQuery client libraries
  - Run setup script (creates dataset/tables)
  - Verify table counts
```

### Phase 3: Deploy Agents

```yaml
deploy-retriever:
  - Build Docker image
  - Push to Artifact Registry
  - Deploy to Cloud Run
  - Configure PUBLIC_URL for A2A

deploy-orchestrator:
  - Build Docker image (includes bigquery_agent folder)
  - Push to Artifact Registry
  - Deploy to Cloud Run
  - Pass RETRIEVER_AGENT_URL from previous step

deploy-ingestion:
  - Upload documents to GCS
  - Build Docker image
  - Deploy to Cloud Run
  - Create Cloud Scheduler job
  - Trigger immediate ingestion
```

### Phase 4: Verification

Deployment summary shows:
- ✅ All service URLs
- ✅ Example test questions
- ✅ Links to test the deployment

## 🧪 Testing Deployment

### Automated Verification

The workflow automatically tests:
```bash
# BigQuery table counts
bq query "SELECT COUNT(*) FROM geography_index.countries"
bq query "SELECT COUNT(*) FROM geography_index.states"
bq query "SELECT COUNT(*) FROM geography_index.districts"
```

### Manual Testing

After deployment completes:

1. **Get orchestrator URL:**
   ```bash
   gcloud run services describe orchestrator-agent \
     --region=europe-west4 \
     --format='value(status.url)'
   ```

2. **Open web UI:**
   ```bash
   # Copy URL from above and open in browser
   ```

3. **Test queries:**
   - **Greeting**: "Hello" (should respond directly)
   - **BigQuery**: "What states are in India?" (queries BigQuery)
   - **RAG**: "Tell me about India's geography" (searches documents)
   - **Combined**: "What is the capital of Maharashtra?" (BQ → RAG flow)

### Check Logs

```bash
# Orchestrator logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=orchestrator-agent" --limit=50

# Retriever logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=retriever-agent" --limit=50

# Ingestion logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ingestion" --limit=50
```

## 💰 Cost Optimization

### During Active Use

Resources running:
- ✅ 3 Cloud Run services (pay per request + idle CPU)
- ✅ RAG corpus storage (~$0.02/GB/month)
- ✅ BigQuery storage (minimal, ~free tier)
- ✅ Artifact Registry storage (~$0.10/GB/month)
- ✅ Cloud Storage (~$0.02/GB/month)

**Estimated cost**: $5-10/month with light usage

### During Idle (After Cleanup)

After running cleanup workflow:
- ❌ Cloud Run services deleted (saves ~80% of costs)
- ✅ BigQuery dataset kept (no cost for small datasets)
- ❌ Old Docker images deleted
- ⚠️ RAG corpus: Optional (can delete if needed)

**Estimated cost**: $1-2/month for storage only

### Best Practices

1. **Deploy when needed:**
   ```bash
   # Push to deploy
   git push origin master
   ```

2. **Cleanup when done:**
   ```bash
   # Via GitHub Actions UI or:
   gh workflow run cleanup.yml -f delete_storage=false -f delete_rag_corpus=false
   ```

3. **Keep RAG corpus:** Saves 5-10 minutes on next deploy

4. **Delete storage:** If documents change frequently, clean and re-ingest

## 🔧 Configuration

### GitHub Secrets/Variables

All required variables are already configured:

| Variable | Value | Purpose |
|----------|-------|---------|
| `GCP_PROJECT_ID` | agenticaigcplearn | GCP project |
| `GCP_PROJECT_NUMBER` | 1073291557100 | Project number |
| `GCP_REGION` | europe-west4 | Deployment region |
| `RAG_CORPUS` | projects/.../ragCorpora/... | Full corpus resource |
| `RAG_CORPUS_ID` | 576460752303423488 | Corpus ID only |
| `GCS_BUCKET` | agenticaigcplearn-adk-docs | Storage bucket |
| `RETRIEVER_AGENT_URL` | (auto-set) | A2A endpoint |
| `ORCHESTRATOR_AGENT_URL` | (auto-set) | Main entry |

### Update Configuration

```bash
# Update a variable
gh variable set RAG_CORPUS_ID --body "NEW_ID"

# List all variables
gh variable list
```

## 🐛 Troubleshooting

### Deployment Failed: BigQuery Setup

**Error**: "Dataset already exists" or "Permission denied"

**Solution**:
```bash
# Check dataset
bq ls geography_index

# Recreate if needed
python infra/setup_bigquery.py
```

### Deployment Failed: Docker Build

**Error**: "COPY failed" or "bigquery_agent not found"

**Solution**: Ensure folder structure is correct:
```
agents/
├── bigquery_agent/
├── orchestrator_agent/
└── retriever_agent/
```

### Runtime Error: "Module not found: bigquery_agent"

**Cause**: Dockerfile build context incorrect

**Solution**: Check deploy.yml line:
```yaml
docker build -t "$IMAGE" -f agents/orchestrator_agent/Dockerfile agents/
#                                                              ^^^^^^ Must be agents/ folder
```

### Cleanup Failed: Corpus Deletion

**Error**: HTTP 404 or 403

**Solution**: Update `RAG_CORPUS_ID` variable:
```bash
# Get corpus ID from orchestrator env vars
gcloud run services describe orchestrator-agent --format=yaml | grep RAG_CORPUS

# Update variable
gh variable set RAG_CORPUS_ID --body "YOUR_CORPUS_ID"
```

## 📊 Monitoring

### Service Status

```bash
# List all services
gcloud run services list --region=europe-west4

# Check specific service
gcloud run services describe orchestrator-agent --region=europe-west4
```

### Resource Usage

```bash
# Cloud Run metrics
gcloud monitoring time-series list \
  --filter='resource.type="cloud_run_revision"' \
  --format="table(metric.type)"

# BigQuery storage
bq show --project_id=agenticaigcplearn geography_index

# GCS storage
gcloud storage du gs://agenticaigcplearn-adk-docs
```

### Costs

View costs at:
- https://console.cloud.google.com/billing/
- Filter by project: agenticaigcplearn
- Group by: Service

## 🔄 Redeploy After Changes

### Update Agent Code

```bash
# Edit code in agents/ folder
vim agents/orchestrator_agent/agent.py

# Commit and push (auto-deploys)
git add -A
git commit -m "Update orchestrator instructions"
git push origin master
```

### Update Documents

```bash
# Edit or add documents
vim data/sample_docs/new_doc.md

# Push to deploy (uploads + re-ingests)
git add -A
git commit -m "Add new documentation"
git push origin master
```

### Update BigQuery Data

```bash
# Edit setup script
vim infra/setup_bigquery.py

# Push to deploy (recreates tables)
git add -A
git commit -m "Add more states/districts"
git push origin master
```

## 📚 Additional Resources

- [Local Testing Guide](../LOCAL_TESTING.md) - Test before deploying
- [Architecture Overview](./ARCHITECTURE.md) - System design
- [Setup Guide](./SETUP.md) - Initial GCP configuration
- [GitHub Actions Docs](https://docs.github.com/en/actions) - Workflow syntax

## 🎯 Next Steps

1. ✅ Deploy to GCP via workflow
2. ✅ Test deployed services
3. ✅ Add more documents to `data/sample_docs/`
4. ✅ Update BigQuery with more sample data
5. ✅ Monitor costs and usage
6. ✅ Cleanup when done testing
