# 🚀 Deployment Summary & Status

## Current Deployment Status

**Workflow:** Deploy ADK agents (Latest)  
**Branch:** master  
**Triggered:** Push to master with workflow fixes  
**Expected Duration:** ~10-15 minutes

### Job Sequence

```
1. cleanup-old-resources (✓ Completes first)
   ├─ Delete old Cloud Run services
   └─ Clean up old Docker images
   
2. setup-bigquery (⏳ Waits for cleanup)
   ├─ Grant BigQuery IAM permissions
   ├─ Create dataset: geography_index
   └─ Create tables: countries, states, districts
   
3. deploy-retriever (⏳ Waits for BigQuery)
   ├─ Build retriever agent Docker image
   ├─ Push to Artifact Registry
   └─ Deploy to Cloud Run (port 8081)
   
4. deploy-orchestrator (⏳ Waits for retriever)
   ├─ Build orchestrator agent Docker image
   ├─ Embed BigQuery agent
   ├─ Push to Artifact Registry
   └─ Deploy to Cloud Run (port 8080)
   
5. deploy-ingestion (⏳ Waits for orchestrator) ← FINAL
   ├─ Upload documents to GCS
   ├─ Build ingestion service Docker image
   ├─ Push to Artifact Registry
   ├─ Deploy to Cloud Run (private)
   ├─ Create Cloud Scheduler job (daily 3 AM)
   ├─ Trigger immediate ingestion
   └─ Print deployment summary
```

## 📋 Deployed Components

### 1. BigQuery Dataset
**Location:** europe-west4  
**Dataset ID:** `geography_index`

#### Tables:
- **countries** (1 row)
  - India with capital, population, area data
  
- **states** (5 rows)
  - Maharashtra, Karnataka, Tamil Nadu, Uttar Pradesh, West Bengal
  
- **districts** (7 rows)
  - Mumbai, Pune, Nagpur (Maharashtra)
  - Bengaluru Urban, Mysuru (Karnataka)
  - Chennai, Coimbatore (Tamil Nadu)

### 2. Cloud Run Services

#### Retriever Agent
- **Service Name:** retriever-agent
- **Role:** RAG specialist using Vertex AI RAG Engine
- **Protocol:** Agent-to-Agent (A2A)
- **Access:** Unauthenticated (for A2A calls from orchestrator)
- **Port:** 8081 (internal)
- **Environment Variables:**
  - `RAG_CORPUS`: Full resource name of RAG corpus
  - `GOOGLE_CLOUD_PROJECT`: agenticaigcplearn
  - `GOOGLE_GENAI_USE_VERTEXAI`: true

#### Orchestrator Agent  
- **Service Name:** orchestrator-agent
- **Role:** Main entry point with web UI
- **Includes:** BigQuery agent (embedded locally for cost-efficiency)
- **Access:** Unauthenticated (public web UI)
- **Port:** 8080 (public)
- **Environment Variables:**
  - `RETRIEVER_AGENT_URL`: URL of retriever A2A service
  - `GOOGLE_CLOUD_PROJECT`: agenticaigcplearn
  - `GOOGLE_GENAI_USE_VERTEXAI`: true

#### Ingestion Service
- **Service Name:** ingestion
- **Role:** Updates RAG corpus from GCS bucket
- **Access:** Private (no unauthenticated access)
- **Schedule:** Daily at 3 AM UTC (Cloud Scheduler)
- **Manual Trigger:** Called immediately after deployment
- **Environment Variables:**
  - `RAG_GCS_SOURCE`: gs://agenticaigcplearn-adk-docs
  - `RAG_CORPUS_ID`: Corpus ID for updates

### 3. Cloud Storage
- **Bucket:** gs://agenticaigcplearn-adk-docs
- **Contents:**
  - districtandplace.md
  - india.md
  - states.md

### 4. Artifact Registry
- **Repository:** adk-agents (europe-west4)
- **Images:**
  - retriever-agent:latest
  - orchestrator-agent:latest
  - ingestion:latest

### 5. Cloud Scheduler
- **Job Name:** ingest-rag-corpus
- **Schedule:** 0 3 * * * (3 AM daily)
- **Target:** Ingestion service
- **Trigger:** Manual + scheduled

## 🧪 Testing the Deployment

Once deployment completes, you can test it immediately:

### Step 1: Get the Orchestrator URL
```bash
gcloud run services describe orchestrator-agent \
  --region=europe-west4 \
  --format='value(status.url)'
```

### Step 2: Open in Browser
Paste the URL from above into your browser to see the web UI.

### Step 3: Test Different Query Types

#### Test 1: Greeting (No Delegation)
```
Question: "Hello"
Expected: Direct response from orchestrator
```

#### Test 2: BigQuery Agent (Metadata Search)
```
Question: "What states are in India?"
Expected: 
  1. Delegates to BigQuery agent
  2. Returns: Maharashtra, Karnataka, Tamil Nadu, Uttar Pradesh, West Bengal
```

#### Test 3: RAG Agent (Document Search)
```
Question: "Tell me about India's geography"
Expected:
  1. Delegates to retriever agent
  2. Searches RAG corpus
  3. Returns content from markdown documents with citations
```

#### Test 4: Combined Flow (BigQuery → RAG)
```
Question: "What is the capital of Maharashtra?"
Expected Flow:
  1. Orchestrator delegates to BigQuery agent
  2. BigQuery searches states table → finds Maharashtra, capital=Mumbai
  3. Orchestrator delegates to Retriever with BQ context
  4. Retriever searches RAG corpus for "Mumbai" with context
  5. Returns combined answer with metadata + document context
```

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User / Web Browser                        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS (public)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator Agent (Cloud Run)                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ FastAPI Web Server + ADK Agent                         │ │
│  │ ┌──────────────────┐                                   │ │
│  │ │ BigQuery Agent   │ (Embedded sub-agent)              │ │
│  │ │ ├─ search_countries()                                │ │
│  │ │ ├─ search_states()                                   │ │
│  │ │ └─ search_districts()                                │ │
│  │ └──────────────────┘                                   │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────┬──────────────────────────────┬─────────────────┘
             │ A2A Protocol (internal)      │ SQL Query
             │                              │
             ▼                              ▼
┌──────────────────────────┐    ┌─────────────────────────┐
│  Retriever Agent         │    │  BigQuery               │
│  (Cloud Run)             │    │  Dataset: geography_index
│  ┌────────────────────┐  │    │  ├─ countries           │
│  │ RAG Specialist     │  │    │  ├─ states              │
│  │ retrieve_from_rag()│  │    │  └─ districts           │
│  └────────────────────┘  │    └─────────────────────────┘
└──────────────┬───────────┘
               │ RAG Query
               ▼
┌──────────────────────────────────┐
│  Vertex AI RAG Engine            │
│  Corpus: 576460752303423488      │
│  ├─ districtandplace.md          │
│  ├─ india.md                     │
│  └─ states.md                    │
└──────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Google Cloud Storage            │
│  Bucket: agenticaigcplearn-docs  │
│  (Source documents)              │
└──────────────────────────────────┘
               ▲
               │ Upload (nightly + on-deploy)
               │
┌──────────────────────────────────┐
│  Ingestion Service (Cloud Run)   │
│  Cloud Scheduler (3 AM daily)    │
└──────────────────────────────────┘
```

## 🔄 Data Flow Example

**User Question:** "What is the capital of Maharashtra?"

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Orchestrator receives query                               │
│    Question: "What is the capital of Maharashtra?"           │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Orchestrator delegates to BigQuery Agent                  │
│    Task: Search for Maharashtra                              │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. BigQuery Agent queries states table                       │
│    Query: SELECT * FROM states WHERE name LIKE '%Maharashtra%'
│    Result: {id: 1, name: "Maharashtra", capital: "Mumbai", ...}
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Orchestrator gets BQ metadata (state_id=1, capital=Mumbai)│
│    Then delegates to Retriever Agent with context            │
│    Context: "Search for information about Mumbai/Maharashtra"│
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Retriever Agent queries RAG corpus                        │
│    Query: "Mumbai Maharashtra capital"                       │
│    Corpus searches markdown documents                        │
│    Result: Matching chunks from districtandplace.md, etc.    │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. Orchestrator combines responses                           │
│    BQ Answer: "Capital of Maharashtra is Mumbai"             │
│    RAG Answer: "Mumbai is the largest city in Maharashtra..." │
│    Combined: Full answer with structured data + context      │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. Response sent to user                                     │
│    "The capital of Maharashtra is Mumbai. Mumbai is..."      │
│    [Sources: BigQuery + RAG documents]                       │
└──────────────────────────────────────────────────────────────┘
```

## 💾 Deployment Files

### Workflow Files
- `.github/workflows/deploy.yml` - Main deployment pipeline
- `.github/workflows/cleanup.yml` - Cost optimization cleanup

### Agent Code
- `agents/orchestrator_agent/` - Main entry point
  - `agent.py` - Orchestrator logic with delegation rules
  - `main.py` - Cloud Run entry point
  - `Dockerfile` - Builds with embedded BigQuery agent
  - `requirements.txt` - Dependencies
  
- `agents/retriever_agent/` - RAG specialist
  - `agent.py` - RAG retrieval logic
  - `a2a_app.py` - A2A protocol server
  - `Dockerfile` - RAG service container
  - `requirements.txt` - Dependencies
  
- `agents/bigquery_agent/` - Metadata index (embedded)
  - `agent.py` - BigQuery search functions
  - `__init__.py` - Package marker

### Infrastructure
- `infra/setup_bigquery.py` - Dataset/table setup script
- `data/sample_docs/` - Source markdown documents

### Documentation
- `docs/DEPLOYMENT.md` - Complete deployment guide
- `docs/ARCHITECTURE.md` - System architecture
- `docs/SETUP.md` - Initial GCP setup
- `LOCAL_TESTING.md` - Local testing guide

## 🔐 Security & Permissions

### Service Account: github-deployer
**Email:** github-deployer@agenticaigcplearn.iam.gserviceaccount.com

**Granted Roles:**
- `roles/artifactregistry.admin` - Push Docker images
- `roles/run.admin` - Deploy Cloud Run services
- `roles/bigquery.dataEditor` - Read/write BigQuery data
- `roles/bigquery.jobUser` - Run BigQuery jobs
- `roles/storage.objectAdmin` - Upload files to GCS
- `roles/iam.serviceAccountUser` - Create service accounts
- `roles/cloudscheduler.jobRunner` - Manage scheduler jobs

### Service Account: scheduler-invoker
**Purpose:** Cloud Scheduler invokes ingestion service  
**Permissions:** `roles/run.invoker`

## 📈 Monitoring & Logs

### View Deployment Logs
```bash
# Latest workflow run
gh run view --log

# All workflow runs
gh run list

# Watch deployment in real-time
gh run watch
```

### View Service Logs
```bash
# Orchestrator logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=orchestrator-agent" --limit=50

# Retriever logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=retriever-agent" --limit=50

# Ingestion logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=ingestion" --limit=50
```

### Monitor Costs
https://console.cloud.google.com/billing/projectslist?project=agenticaigcplearn

## 💰 Cost Breakdown

### Per Month (Active Deployment)
- Cloud Run (orchestrator + retriever): ~$2-5
- BigQuery (storage + queries): ~$0-2
- Cloud Storage: ~$0.05
- Artifact Registry: ~$0.10
- Cloud Scheduler: Free (1 job)

**Total: ~$2-7/month** with moderate usage

### Cost Optimization Tips
1. Use cleanup workflow to stop services when not needed
2. Keep RAG corpus (don't delete) to avoid re-ingestion
3. Monitor query costs with BigQuery insights
4. Schedule ingestion job only when documents change

## ✅ Deployment Checklist

After deployment completes:

- [ ] All three Cloud Run services deployed
- [ ] BigQuery dataset and tables created
- [ ] Documents uploaded to GCS
- [ ] RAG corpus updated
- [ ] Cloud Scheduler job created
- [ ] Test greeting (no delegation)
- [ ] Test BigQuery query
- [ ] Test RAG search
- [ ] Test combined flow
- [ ] Check logs for errors
- [ ] Document deployment URLs

## 🔗 Quick Links

**Deployed Services (after completion):**
- Orchestrator: `gcloud run services describe orchestrator-agent --region=europe-west4 --format='value(status.url)'`
- Retriever: `gcloud run services describe retriever-agent --region=europe-west4 --format='value(status.url)'`
- Ingestion: `gcloud run services describe ingestion --region=europe-west4 --format='value(status.url)'`

**Project Resources:**
- GCP Console: https://console.cloud.google.com/run?project=agenticaigcplearn
- GitHub Actions: https://github.com/abhimasum/GoogleCloudAi/actions
- BigQuery: https://console.cloud.google.com/bigquery?project=agenticaigcplearn
- Cloud Storage: https://console.cloud.google.com/storage/browser?project=agenticaigcplearn

## 📞 Troubleshooting

If deployment fails:

1. **BigQuery setup fails:**
   - Check IAM permissions (roles/bigquery.dataEditor, .jobUser)
   - Verify PROJECT_ID and LOCATION env vars
   - Run setup manually: `python infra/setup_bigquery.py`

2. **Docker build fails:**
   - Check Dockerfile syntax
   - Verify all COPY paths exist
   - Check requirements.txt for typos

3. **Service deployment fails:**
   - Check Cloud Run quotas
   - Verify service account has roles/run.admin
   - Check environment variables

4. **A2A connection fails:**
   - Verify RETRIEVER_AGENT_URL is correct
   - Check orchestrator logs for errors
   - Ensure retriever service is running

For detailed troubleshooting, see [DEPLOYMENT.md](./docs/DEPLOYMENT.md#troubleshooting)
