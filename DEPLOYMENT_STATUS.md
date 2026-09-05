# 🚀 Deployment Summary & Status

## Current Deployment Status

**Workflow:** Deploy MAF agents (Latest)  
**Branch:** master  
**Triggered:** Push to master with workflow fixes  
**Expected Duration:** ~15-20 minutes

### Job Sequence

```
1. provision-infrastructure (✓ Completes first)
   ├─ Create/reuse Azure SQL Database
   ├─ Create/reuse Azure OpenAI (GPT-4o)
   ├─ Create/reuse Azure AI Search
   ├─ Create/reuse Azure Storage
   ├─ Create/reuse Azure Container Registry
   ├─ Create/reuse Container Apps Environment
   └─ Export credentials as job outputs
   
2. setup-database (⏳ Waits for infrastructure)
   ├─ Install ODBC Driver 18 for SQL Server
   ├─ Populate countries table (1 row: India)
   ├─ Populate states table (28 states/UTs)
   └─ Populate districts table (sample data)
   
3. build-and-push-images (⏳ Waits for database)
   ├─ Build SQL Agent Docker image
   ├─ Build Retriever Agent Docker image
   ├─ Build Orchestrator Agent Docker image
   ├─ Push all images to Azure Container Registry
   └─ Store image references
   
4. deploy-retriever (⏳ Waits for build)
   ├─ Deploy Retriever Agent to Container Apps
   ├─ Wire Azure AI Search credentials
   └─ Output public URL
   
5. deploy-orchestrator (⏳ Waits for retriever) ← FINAL
   ├─ Deploy Orchestrator Agent to Container Apps
   ├─ Wire SQL + Retriever credentials
   ├─ Point to Retriever service
   └─ Output public URL
```

## 📋 Deployed Components

### 1. Azure SQL Database
**Region:** westeurope  
**Server:** ai-agents-sql
**Database:** geography_db

#### Tables:
- **countries** (1 row)
  - India with capital, population, area data
  
- **states** (28 rows)
  - All Indian states and union territories
  
- **districts** (sample rows)
  - Sample districts with state references

### 2. Container Apps Services

#### Retriever Agent
- **Service Name:** retriever-agent
- **Role:** RAG specialist using Azure AI Search
- **Protocol:** HTTP REST (A2A via URLs)
- **Access:** Unauthenticated (for A2A calls from orchestrator)
- **Port:** 8080
- **Environment Variables:**
  - `AZURE_SEARCH_ENDPOINT`: Azure AI Search instance URL
  - `AZURE_SEARCH_KEY`: Search service API key
  - `AZURE_SEARCH_INDEX`: geography-docs
  - `AZURE_OPENAI_ENDPOINT`: OpenAI instance URL
  - `AZURE_OPENAI_KEY`: OpenAI API key
  - `AZURE_OPENAI_DEPLOYMENT`: gpt-4o

#### Orchestrator Agent  
- **Service Name:** orchestrator-agent
- **Role:** Main entry point with web UI
- **Protocol:** HTTPS (public web interface)
- **Access:** Unauthenticated (public web UI)
- **Port:** 8080
- **Environment Variables:**
  - `RETRIEVER_AGENT_URL`: URL of retriever Container App service
  - `AZURE_OPENAI_ENDPOINT`: OpenAI instance URL
  - `AZURE_OPENAI_KEY`: OpenAI API key
  - `AZURE_OPENAI_DEPLOYMENT`: gpt-4o
  - `AZURE_SQL_SERVER`: SQL server address
  - `AZURE_SQL_DATABASE`: geography_db
  - `AZURE_SQL_USER`: Database username
  - `AZURE_SQL_PASSWORD`: Database password

### 3. Azure Storage
- **Account:** aiagentsstorageabhimasum
- **Containers:**
  - geography-docs (ingested documents)
  
- **Contents:**
  - districtandplace.md
  - india.md
  - states.md

### 4. Azure Container Registry
- **Registry:** aiagentsacr (westeurope)
- **Images:**
  - sql-agent:latest
  - retriever-agent:latest
  - orchestrator-agent:latest

### 5. Azure OpenAI & AI Search
- **OpenAI Deployment:** ai-agents-openai
  - Model: GPT-4o (2024-11-20)
  - Region: westeurope
  - SKU: GlobalStandard
  
- **AI Search Service:** ai-agents-search-abhimasum
  - SKU: Basic
  - Index: geography-docs (vector search enabled)

## 🧪 Testing the Deployment

Once deployment completes, you can test it immediately:

### Step 1: Get the Orchestrator URL
```bash
az containerapp show \
  --resource-group azure-ai-agents \
  --name orchestrator-agent \
  --query properties.configuration.ingress.fqdn \
  -o tsv
```

### Step 2: Open in Browser
Paste the URL from above into your browser (with `https://` prefix) to see the web UI.

### Step 3: Test Different Query Types

#### Test 1: Greeting (No Delegation)
```
Question: "Hello"
Expected: Direct response from orchestrator
```

#### Test 2: SQL Agent (Metadata Search)
```
Question: "What states are in India?"
Expected: 
  1. Delegates to SQL agent
  2. Returns: All 28 states and union territories
```

#### Test 3: RAG Agent (Document Search)
```
Question: "Tell me about India's geography"
Expected:
  1. Delegates to retriever agent
  2. Searches Azure AI Search index
  3. Returns content from markdown documents with citations
```

#### Test 4: Combined Flow (SQL → RAG)
```
Question: "What is the capital of Maharashtra?"
Expected Flow:
  1. Orchestrator delegates to SQL agent
  2. SQL queries states table → finds Maharashtra, capital=Mumbai
  3. Orchestrator delegates to Retriever with SQL context
  4. Retriever searches AI Search for "Mumbai" with context
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
│         Orchestrator Agent (Container Apps)                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ FastAPI Web Server + MAF Agent                         │ │
│  │ ├─ Routes queries to SQL or Retriever agents           │ │
│  │ └─ Combines responses from both specialists            │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────┬──────────────────────────────┬─────────────────┘
             │ HTTP REST (A2A)              │ pyodbc
             │                              │
             ▼                              ▼
┌──────────────────────────────┐   ┌─────────────────────────┐
│  Retriever Agent             │   │  Azure SQL Database     │
│  (Container Apps)            │   │  Server: ai-agents-sql  │
│  ┌────────────────────────┐  │   │  Database: geography_db │
│  │ RAG Specialist         │  │   │  ├─ countries           │
│  │ search_documents()     │  │   │  ├─ states (28 rows)    │
│  └────────────────────────┘  │   │  └─ districts           │
└──────────────┬───────────────┘   └─────────────────────────┘
               │ Vector Search
               ▼
┌──────────────────────────────────┐
│  Azure AI Search                 │
│  Service: ai-agents-search-*     │
│  Index: geography-docs           │
│  ├─ districtandplace.md (chunks) │
│  ├─ india.md (chunks)            │
│  └─ states.md (chunks)           │
└──────────────────────────────────┘
               │
               ▲
               │ Upload/Index
               │
┌──────────────────────────────────┐
│  Azure Storage Blob              │
│  Account: aiagentsstorage*       │
│  Container: geography-docs       │
│  ├─ districtandplace.md          │
│  ├─ india.md                     │
│  └─ states.md                    │
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
│ 2. Orchestrator delegates to SQL Agent                       │
│    Task: Search for Maharashtra in database                  │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. SQL Agent queries states table via pyodbc                 │
│    Query: SELECT * FROM states WHERE name LIKE '%Maharashtra%'
│    Result: {id: 1, name: "Maharashtra", capital: "Mumbai"...}
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Orchestrator gets SQL metadata (state_id=1, capital=Mumbai)│
│    Then delegates to Retriever Agent with context            │
│    Context: "Search for information about Mumbai/Maharashtra"│
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Retriever Agent queries Azure AI Search                   │
│    Vector Query: "Mumbai Maharashtra capital"                │
│    Search performs semantic matching on indexed documents    │
│    Result: Matching chunks from geography-docs               │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. Orchestrator combines responses                           │
│    SQL Answer: "Capital of Maharashtra is Mumbai"            │
│    RAG Answer: "Mumbai is the largest city in Maharashtra..."│
│    Combined: Full answer with structured data + context      │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. Response sent to user                                     │
│    "The capital of Maharashtra is Mumbai. Mumbai is..."      │
│    [Sources: SQL Database + Search Index]                    │
└──────────────────────────────────────────────────────────────┘
```

## 💾 Deployment Files

### Workflow Files
- `.github/workflows/deploy.yml` - Main deployment pipeline
- `.github/workflows/cleanup.yml` - Cost optimization cleanup

### Agent Code
- `agents/orchestrator_agent/` - Main entry point
  - `agent.py` - Orchestrator logic with delegation rules
  - `main.py` - Container Apps entry point
  - `Dockerfile` - Builds agent container
  - `requirements.txt` - Dependencies
  
- `agents/retriever_agent/` - RAG specialist
  - `agent.py` - RAG retrieval logic
  - `a2a_app.py` - A2A protocol server
  - `Dockerfile` - RAG service container
  - `requirements.txt` - Dependencies
  
- `agents/sql_agent/` - SQL metadata queries
  - `agent.py` - SQL query functions
  - `__init__.py` - Package marker
  - `requirements.txt` - Dependencies

### Infrastructure
- `infra/setup_azure_sql.py` - Database/table setup script
- `infra/setup_azure.sh` - Azure resource setup script
- `data/sample_docs/` - Source markdown documents

### Documentation
- `docs/DEPLOYMENT.md` - Complete deployment guide
- `docs/ARCHITECTURE.md` - System architecture
- `docs/SETUP.md` - Initial Azure setup
- `LOCAL_TESTING.md` - Local testing guide

## 🔐 Security & Permissions

### Service Principal: github-actions-azureai
**Created for:** Automated GitHub Actions deployments  
**Scope:** Azure subscription with Contributor role

**Managed Permissions (Auto-assigned by Pipeline):**
- Container Apps management (deploy & update)
- SQL Database management (create/modify tables)
- OpenAI service access (model deployments)
- AI Search management (index operations)
- Storage account access (blob operations)
- Container Registry push (image uploads)

### Access Control
- **Orchestrator URL:** Public (unauthenticated web UI)
- **Retriever URL:** Public (for A2A calls from orchestrator)
- **Database:** Private (only accessible from Container Apps)
- **Storage:** Private (only via Container Apps identity)

## 📈 Monitoring & Logs

### View Deployment Logs
```bash
# Check workflow status
git log --oneline | head -10

# View Azure resource status
az resource list --resource-group azure-ai-agents --output table

# Check Container Apps status
az containerapp list --resource-group azure-ai-agents
```

### View Service Logs
```bash
# Orchestrator logs
az containerapp logs show \
  --name orchestrator-agent \
  --resource-group azure-ai-agents \
  --follow

# Retriever logs
az containerapp logs show \
  --name retriever-agent \
  --resource-group azure-ai-agents \
  --follow

# SQL connection logs (from application)
# Check orchestrator agent logs for pyodbc connection issues
```

### Monitor Costs
Open Azure Portal: https://portal.azure.com  
Navigate to: Cost Management + Billing → Cost Analysis

## 💰 Cost Breakdown

### Per Month (Active Deployment)
- **Azure SQL Database**: ~$5-10 (Basic tier, pay-as-you-go)
- **Azure OpenAI (GPT-4o)**: ~$10-30 (token-based, light usage)
- **AI Search**: ~$50-75 (Basic tier with vector search)
- **Container Apps**: ~$15-30 (consumption plan, light workload)
- **Azure Storage**: ~$0.50
- **Container Registry**: ~$5

**Total: ~$85-150/month** for dev/test environment

### Cost Optimization Tips
1. Use Container Apps consumption plan (scale to zero when idle)
2. Use SQL Database Basic tier (pay-per-query model)
3. Monitor OpenAI token usage via Azure portal
4. Archive old documents in cold storage
5. Set up budget alerts in Cost Management

## ✅ Deployment Checklist

After deployment completes:

- [ ] All Container Apps services deployed
- [ ] Azure SQL database and tables created  
- [ ] Documents uploaded to Azure Storage
- [ ] AI Search index populated
- [ ] Container Registry has all three images
- [ ] Test greeting (no delegation)
- [ ] Test SQL query
- [ ] Test RAG search
- [ ] Test combined flow
- [ ] Check Application Insights logs (optional)
- [ ] Document deployment URLs

## 🔗 Quick Links

**Deployed Services (after completion):**
```bash
# Get Orchestrator URL
az containerapp show \
  --name orchestrator-agent \
  --resource-group azure-ai-agents \
  --query properties.configuration.ingress.fqdn \
  -o tsv

# Get Retriever URL
az containerapp show \
  --name retriever-agent \
  --resource-group azure-ai-agents \
  --query properties.configuration.ingress.fqdn \
  -o tsv
```

**Azure Resources:**
- Azure Portal: https://portal.azure.com
- Container Apps: https://portal.azure.com → Container Apps
- SQL Database: https://portal.azure.com → SQL Databases → geography_db
- AI Search: https://portal.azure.com → Search services
- Storage Account: https://portal.azure.com → Storage Accounts
- GitHub Actions: https://github.com/abhimasum/AzureCloudAi/actions

## 📞 Troubleshooting

If deployment fails:

1. **SQL connection fails:**
   - Check SQL server firewall rules (allow Container Apps subnet)
   - Verify ODBC Driver 18 installed on runner
   - Check username/password in secrets
   - Run `sqlcmd` test manually

2. **Docker build fails:**
   - Check Dockerfile syntax
   - Verify all COPY paths exist
   - Check requirements.txt for typos
   - Ensure no bigquery_agent references

3. **Container Apps deployment fails:**
   - Check Container Registry credentials
   - Verify image exists in ACR
   - Check environment variables
   - Look at deployment logs in portal

4. **AI Search indexing fails:**
   - Verify Search service access key
   - Check index schema exists
   - Verify Storage account has correct permissions
   - Check document format is supported

For detailed troubleshooting, see [DEPLOYMENT.md](./docs/DEPLOYMENT.md#troubleshooting)
