# Azure Setup Guide: Multi-Agent System with MAF

**Complete step-by-step guide** to deploy the Azure multi-agent system using your account (**abhimausm2@gmail.com**).

---

## 📋 Prerequisites

Before starting, ensure you have:

1. **Azure Account**: abhimausm2@gmail.com (with active subscription)
2. **Azure CLI**: `az --version` (v2.50+)
3. **Python**: `python --version` (3.11+)
4. **Git**: `git --version`
5. **GitHub Account**: With access to `abhimasum/AzureCloudAi` repo

### Verify Prerequisites

```powershell
# Check Azure CLI
az --version

# Login to Azure
az login
# Opens browser - sign in with abhimausm2@gmail.com

# Verify subscription
az account show

# Check Python
python --version

# Check Git
git --version
```

---

## 🚀 Part 1: Azure Infrastructure Setup (One-Time)

### Step 1: Run Automated Setup Script

The `setup_azure.sh` script creates all required Azure resources:

```bash
cd AzureCloudAi
bash infra/setup_azure.sh
```

**What it creates:**
1. Resource Group: `azure-ai-agents`
2. Azure SQL Server + Database (`geography_index`)
3. Azure OpenAI Service (GPT-4o deployment)
4. Azure AI Search Service
5. Azure Blob Storage (document container)
6. Azure Container Registry
7. Container Apps Environment

**Interactive prompts** (accept defaults or customize):
- Resource Group name: `azure-ai-agents`
- Location: `eastus` (or your preferred region)
- SQL Server name: Auto-generated
- SQL Admin username: `sqladmin`
- SQL Admin password: **Choose strong password** (min 12 chars)

**Setup time**: ~10-15 minutes

### Step 2: Save Credentials

The script outputs all credentials at the end. **Copy them to `.env` file**:

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
notepad .env  # Windows
# OR
nano .env     # Linux/Mac
```

**Required variables** (from setup script output):

```env
# Azure SQL
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=geography_index
AZURE_SQL_USERNAME=sqladmin
AZURE_SQL_PASSWORD=your-strong-password

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-search-key
AZURE_SEARCH_INDEX=documents

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_STORAGE_CONTAINER=documents
```

### Step 3: Verify Database Schema

The setup script automatically creates tables. Verify:

```bash
python infra/setup_azure_sql.py
```

**Expected output:**
```
✓ Connected to Azure SQL Database
✓ Countries table created
✓ States table already has data
✓ Districts table already has data

=== Database Summary ===
Countries: 1
States/UTs: 36
Districts: 13
```

---

## 🧪 Part 2: Local Testing

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Key packages:**
- `agent-framework>=1.16.0` (Microsoft Agent Framework)
- `azure-identity`, `azure-ai-openai`
- `azure-search-documents`
- `pyodbc` (Azure SQL connector)

### Step 2: Upload Sample Documents

Upload documents to Azure Blob Storage:

```bash
# Using Azure CLI
az storage blob upload-batch \
  --account-name YOUR_STORAGE_ACCOUNT \
  --destination documents \
  --source data/sample_docs/ \
  --auth-mode login
```

**OR** use Azure Portal:
1. Go to Storage Account → Containers → `documents`
2. Upload files from `data/sample_docs/`:
   - `india.md`
   - `states.md`
   - `districtandplace.md`

### Step 3: Run Ingestion Service

Index documents into Azure AI Search:

```bash
python ingestion/main.py
```

**Expected output:**
```
✓ Loaded 3 documents from Azure Blob Storage
✓ Generated embeddings using Azure OpenAI
✓ Indexed 3 documents into Azure AI Search
```

### Step 4: Test Individual Agents

**Test SQL Agent:**
```bash
cd agents/sql_agent
python agent.py
```

**Test Retriever Agent:**
```bash
cd agents/retriever_agent
python agent.py
```

**Test Orchestrator (main entry point):**
```bash
cd agents/orchestrator_agent
python main.py
```

Open browser: `http://localhost:8002`

**Test queries:**
- "Tell me about India"
- "What is the capital of Maharashtra?"
- "List all Indian states"
- "Tell me about the culture of Maharashtra"

---

## 🔐 Part 3: GitHub Setup for CI/CD

### Step 1: Configure GitHub Secrets

Go to: `https://github.com/abhimasum/AzureCloudAi/settings/secrets/actions`

Click **"New repository secret"** and add:

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `AZURE_CREDENTIALS` | Service Principal JSON | See below |
| `AZURE_SQL_CONNECTION_STRING` | Connection string | From `.env` |
| `AZURE_OPENAI_ENDPOINT` | OpenAI endpoint | From `.env` |
| `AZURE_OPENAI_API_KEY` | OpenAI key | From `.env` |
| `AZURE_SEARCH_ENDPOINT` | Search endpoint | From `.env` |
| `AZURE_SEARCH_KEY` | Search key | From `.env` |
| `AZURE_STORAGE_CONNECTION_STRING` | Storage connection | From `.env` |
| `ACR_LOGIN_SERVER` | Registry URL | `yourregistry.azurecr.io` |
| `ACR_USERNAME` | Registry username | From ACR admin |
| `ACR_PASSWORD` | Registry password | From ACR admin |

### Step 2: Create Service Principal for GitHub

```bash
# Get subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Create service principal
az ad sp create-for-rbac \
  --name "github-actions-azureai" \
  --role "Contributor" \
  --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/azure-ai-agents" \
  --sdk-auth

# Copy the entire JSON output to AZURE_CREDENTIALS secret
```

**Output format:**
```json
{
  "clientId": "xxx",
  "clientSecret": "xxx",
  "subscriptionId": "xxx",
  "tenantId": "xxx",
  ...
}
```

### Step 3: Get ACR Credentials

```bash
# Get ACR login server
az acr show --name YOUR_ACR_NAME --query loginServer -o tsv

# Enable admin access
az acr update --name YOUR_ACR_NAME --admin-enabled true

# Get credentials
az acr credential show --name YOUR_ACR_NAME
```

Add to GitHub secrets:
- `ACR_LOGIN_SERVER`: Output from first command
- `ACR_USERNAME`: Output `username` field
- `ACR_PASSWORD`: Output `passwords[0].value`

---

## 🚢 Part 4: Deploy to Azure

### Option 1: Automated Deploy (GitHub Actions)

```bash
# Commit and push
git add -A
git commit -m "Initial Azure deployment"
git push origin master
```

**GitHub Actions will:**
1. Build Docker images for 3 agents
2. Push to Azure Container Registry
3. Deploy to Azure Container Apps
4. Run database migrations
5. Index documents into AI Search

**Monitor progress**: 
- Go to: `https://github.com/abhimasum/AzureCloudAi/actions`
- Click latest workflow run

**Deployment time**: ~8-12 minutes

### Option 2: Manual Deploy

**Build and push images:**
```bash
# Login to ACR
az acr login --name YOUR_ACR_NAME

# Build and push orchestrator
docker build -t yourregistry.azurecr.io/orchestrator:latest agents/orchestrator_agent
docker push yourregistry.azurecr.io/orchestrator:latest

# Build and push retriever
docker build -t yourregistry.azurecr.io/retriever:latest agents/retriever_agent
docker push yourregistry.azurecr.io/retriever:latest
```

**Deploy Container Apps:**
```bash
# Deploy orchestrator
az containerapp create \
  --name orchestrator \
  --resource-group azure-ai-agents \
  --environment ai-agents-env \
  --image yourregistry.azurecr.io/orchestrator:latest \
  --target-port 8002 \
  --ingress external \
  --registry-server yourregistry.azurecr.io \
  --registry-username YOUR_ACR_USERNAME \
  --registry-password YOUR_ACR_PASSWORD \
  --env-vars \
    AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \
    AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY \
    AZURE_SQL_SERVER=$AZURE_SQL_SERVER \
    AZURE_SEARCH_ENDPOINT=$AZURE_SEARCH_ENDPOINT
```

---

## ✅ Part 5: Verify Deployment

### Get Container Apps URLs

```bash
# Get orchestrator URL
az containerapp show \
  --name orchestrator \
  --resource-group azure-ai-agents \
  --query properties.configuration.ingress.fqdn -o tsv
```

### Test Production Deployment

Open orchestrator URL in browser: `https://orchestrator-xxx.azurecontainerapps.io`

**Test queries:**
1. "Hello" → Should get greeting
2. "List all states" → Should return 28 states from SQL
3. "What is the capital of Karnataka?" → Should return "Bengaluru"
4. "Tell me about Maharashtra culture" → Should retrieve from AI Search

### Check Logs

```bash
# View orchestrator logs
az containerapp logs show \
  --name orchestrator \
  --resource-group azure-ai-agents \
  --tail 50
```

---

## 🔧 Troubleshooting

### Issue 1: SQL Connection Failed

**Error**: "Login failed for user"

**Fix:**
```bash
# Add your IP to firewall
az sql server firewall-rule create \
  --resource-group azure-ai-agents \
  --server YOUR_SQL_SERVER \
  --name AllowMyIP \
  --start-ip-address YOUR_PUBLIC_IP \
  --end-ip-address YOUR_PUBLIC_IP
```

### Issue 2: Azure OpenAI Rate Limits

**Error**: "Rate limit exceeded"

**Fix:**
```bash
# Increase deployment capacity
az cognitiveservices account deployment update \
  --name YOUR_OPENAI_NAME \
  --resource-group azure-ai-agents \
  --deployment-name gpt-4o \
  --sku-capacity 20
```

### Issue 3: AI Search Index Empty

**Error**: "No results found"

**Fix:**
```bash
# Re-run ingestion
python ingestion/main.py
```

---

## 💰 Cost Management

### Monitor Spending

```bash
# Check current costs
az consumption usage list \
  --start-date 2026-08-01 \
  --end-date 2026-09-01 \
  --query "[?contains(instanceName, 'ai-agents')]"
```

### Cleanup Resources

**Delete everything:**
```bash
az group delete --name azure-ai-agents --yes
```

---

## 📚 Next Steps

1. **Customize Agents**: Edit agent instructions in `agents/*/agent.py`
2. **Add More Data**: Upload documents to Blob Storage and re-run ingestion
3. **Monitor Performance**: Setup Application Insights
4. **Setup Alerts**: Configure Azure Monitor
5. **Production Hardening**: Add authentication, rate limiting

---

## 🔗 Additional Resources

- [Microsoft Agent Framework Docs](https://microsoft.github.io/agent-framework/)
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
- [Azure AI Search](https://azure.microsoft.com/en-us/products/ai-services/ai-search)
- [Azure Container Apps](https://azure.microsoft.com/en-us/products/container-apps)
