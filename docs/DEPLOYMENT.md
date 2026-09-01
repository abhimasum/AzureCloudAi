# Deployment Guide: Azure Container Apps

This guide explains how to deploy and manage the multi-agent system on **Azure Container Apps** using **GitHub Actions**.

---

## 🚀 Quick Deploy

### Option 1: Automatic Deploy (Push to Master)

Any push to the `master` branch automatically triggers deployment:

```bash
git add -A
git commit -m "Deploy to Azure"
git push origin master
```

The GitHub Actions workflow will:
1. ✅ Login to Azure using service principal
2. ✅ Build Docker images for all agents
3. ✅ Push images to Azure Container Registry
4. ✅ Deploy/update Container Apps
5. ✅ Verify deployments
6. ✅ Run post-deployment tests

**Deployment time**: ~8-12 minutes

### Option 2: Manual Deploy (GitHub Actions UI)

1. Go to: https://github.com/abhimasum/AzureCloudAi/actions
2. Select "Deploy to Azure" workflow
3. Click "Run workflow"
4. Choose branch: `master`
5. Click "Run workflow"

---

## 📋 Prerequisites for GitHub Actions

### Step 1: Setup Azure Resources

Run the setup script (one-time):
```bash
bash infra/setup_azure.sh
```

This creates:
- Resource Group: `azure-ai-agents`
- Azure SQL Server + Database
- Azure OpenAI Service
- Azure AI Search
- Azure Blob Storage
- Azure Container Registry
- Container Apps Environment

### Step 2: Configure GitHub Secrets

Go to: `https://github.com/abhimasum/AzureCloudAi/settings/secrets/actions`

Add these secrets:

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `AZURE_CREDENTIALS` | Service Principal JSON | `az ad sp create-for-rbac --sdk-auth` |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID | `az account show --query id -o tsv` |
| `AZURE_RESOURCE_GROUP` | `azure-ai-agents` | From setup script |
| `AZURE_LOCATION` | `eastus` | From setup script |
| `ACR_LOGIN_SERVER` | `yourregistry.azurecr.io` | `az acr show --query loginServer` |
| `ACR_USERNAME` | Registry username | `az acr credential show` |
| `ACR_PASSWORD` | Registry password | `az acr credential show` |
| `AZURE_SQL_CONNECTION_STRING` | SQL connection string | From `.env` file |
| `AZURE_OPENAI_ENDPOINT` | OpenAI endpoint | From `.env` file |
| `AZURE_OPENAI_API_KEY` | OpenAI API key | From `.env` file |
| `AZURE_SEARCH_ENDPOINT` | AI Search endpoint | From `.env` file |
| `AZURE_SEARCH_KEY` | AI Search key | From `.env` file |
| `AZURE_STORAGE_CONNECTION_STRING` | Storage connection | From `.env` file |

#### Create Service Principal

```bash
# Create service principal with Contributor role
az ad sp create-for-rbac \
  --name "github-actions-azureai" \
  --role "Contributor" \
  --scopes "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/azure-ai-agents" \
  --sdk-auth

# Copy entire JSON output to AZURE_CREDENTIALS secret
```

#### Get ACR Credentials

```bash
# Get ACR name
ACR_NAME=$(az acr list --resource-group azure-ai-agents --query "[0].name" -o tsv)

# Enable admin access
az acr update --name $ACR_NAME --admin-enabled true

# Get credentials
az acr credential show --name $ACR_NAME

# Copy:
# - loginServer → ACR_LOGIN_SERVER
# - username → ACR_USERNAME
# - passwords[0].value → ACR_PASSWORD
```

---

## 📦 What Gets Deployed

### Container Apps (3 Services)

1. **orchestrator**
   - Main entry point with web UI
   - Embeds SQL agent for geography queries
   - Delegates to retriever via A2A protocol
   - URL: `https://orchestrator-xxx.azurecontainerapps.io`
   - Scaling: 0-10 instances

2. **retriever**
   - RAG specialist using Azure AI Search
   - Exposes A2A protocol for agent-to-agent calls
   - URL: `https://retriever-xxx.azurecontainerapps.io`
   - Scaling: 0-5 instances

3. **ingestion** (optional, scheduled)
   - Updates AI Search index from Blob Storage
   - Runs on-demand or scheduled
   - Internal service (no public ingress)

### Azure Container Registry

- **Repository**: `yourregistry.azurecr.io`
- **Images**: 
  - `orchestrator:latest`
  - `orchestrator:<git-sha>`
  - `retriever:latest`
  - `retriever:<git-sha>`
  - `ingestion:latest`
  - `ingestion:<git-sha>`

### Azure SQL Database

- **Database**: `geography_index`
- **Tables**:
  - `countries` (1 row: India)
  - `states` (36 rows: 28 states + 8 UTs)
  - `districts` (13 sample districts)

### Azure Blob Storage

- **Container**: `documents`
- **Contents**: Markdown documents from `data/sample_docs/`

### Azure AI Search

- **Index**: `documents`
- **Fields**: id, content, title, embedding
- **Algorithm**: HNSW vector search

---

## 🔄 GitHub Actions Workflow

### Workflow File: `.github/workflows/deploy.yml`

**Triggers:**
- Push to `master` branch
- Manual workflow dispatch
- Pull request to `master` (test only, no deploy)

**Jobs:**

1. **Build & Push Images**
   ```yaml
   - Login to Azure
   - Login to ACR
   - Build Docker images (orchestrator, retriever, ingestion)
   - Tag with :latest and :git-sha
   - Push to ACR
   ```

2. **Deploy Container Apps**
   ```yaml
   - Deploy orchestrator (with all environment variables)
   - Deploy retriever (with Search + OpenAI config)
   - Deploy ingestion (scheduled job)
   - Wait for deployments to stabilize
   ```

3. **Post-Deployment Verification**
   ```yaml
   - Get Container App URLs
   - Health check orchestrator endpoint
   - Test sample query
   - Check logs for errors
   ```

**Environment Variables Injected:**
```yaml
AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
AZURE_OPENAI_DEPLOYMENT: gpt-4o
AZURE_SQL_SERVER: (from connection string)
AZURE_SQL_DATABASE: geography_index
AZURE_SQL_USERNAME: (from connection string)
AZURE_SQL_PASSWORD: (from connection string)
AZURE_SEARCH_ENDPOINT: ${{ secrets.AZURE_SEARCH_ENDPOINT }}
AZURE_SEARCH_KEY: ${{ secrets.AZURE_SEARCH_KEY }}
AZURE_SEARCH_INDEX: documents
RETRIEVER_URL: https://retriever-xxx.azurecontainerapps.io
```

---

## 🧹 Cleanup Resources

### Option 1: Via GitHub Actions (Recommended)

Create `.github/workflows/cleanup.yml`:

```yaml
name: 🧹 Cleanup Resources

on:
  workflow_dispatch:
    inputs:
      delete_container_apps:
        description: 'Delete Container Apps'
        required: true
        type: boolean
        default: true
      delete_acr_images:
        description: 'Delete old ACR images'
        required: true
        type: boolean
        default: true
      delete_all:
        description: 'Delete entire resource group'
        required: true
        type: boolean
        default: false
```

**Run cleanup:**
1. Go to: https://github.com/abhimasum/AzureCloudAi/actions
2. Select "🧹 Cleanup Resources" workflow
3. Click "Run workflow"
4. Choose what to delete
5. Click "Run workflow"

### Option 2: Via Azure CLI

**Delete specific Container Apps:**
```bash
az containerapp delete --name orchestrator --resource-group azure-ai-agents
az containerapp delete --name retriever --resource-group azure-ai-agents
az containerapp delete --name ingestion --resource-group azure-ai-agents
```

**Delete old ACR images:**
```bash
# List images
az acr repository list --name $ACR_NAME

# Delete old tags (keep latest)
az acr repository show-tags --name $ACR_NAME --repository orchestrator
az acr repository delete --name $ACR_NAME --image orchestrator:old-sha --yes
```

**Delete entire resource group (⚠️ deletes EVERYTHING):**
```bash
az group delete --name azure-ai-agents --yes --no-wait
```

---

## 🔍 Monitoring & Debugging

### Get Container App URLs

```bash
# Orchestrator URL (user-facing)
az containerapp show \
  --name orchestrator \
  --resource-group azure-ai-agents \
  --query properties.configuration.ingress.fqdn -o tsv

# Retriever URL (A2A endpoint)
az containerapp show \
  --name retriever \
  --resource-group azure-ai-agents \
  --query properties.configuration.ingress.fqdn -o tsv
```

### View Logs

**Real-time logs:**
```bash
# Orchestrator logs
az containerapp logs show \
  --name orchestrator \
  --resource-group azure-ai-agents \
  --follow

# Retriever logs
az containerapp logs show \
  --name retriever \
  --resource-group azure-ai-agents \
  --follow
```

**Recent logs (last 50 lines):**
```bash
az containerapp logs show \
  --name orchestrator \
  --resource-group azure-ai-agents \
  --tail 50
```

### Check Deployment Status

```bash
# Get orchestrator status
az containerapp show \
  --name orchestrator \
  --resource-group azure-ai-agents \
  --query properties.runningStatus -o tsv

# Get revision status
az containerapp revision list \
  --name orchestrator \
  --resource-group azure-ai-agents \
  --query "[].{Name:name, Status:properties.runningStatus, CreatedTime:properties.createdTime}" -o table
```

### Test Endpoints

**Health check:**
```bash
curl https://orchestrator-xxx.azurecontainerapps.io/health
```

**Test query:**
```bash
curl -X POST https://orchestrator-xxx.azurecontainerapps.io/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### View Application Insights (if configured)

```bash
# Get Application Insights connection string
az monitor app-insights component show \
  --app ai-agents-insights \
  --resource-group azure-ai-agents \
  --query connectionString -o tsv
```

Then view in Azure Portal: `https://portal.azure.com → Application Insights`

---

## 🔧 Troubleshooting

### Issue 1: Deployment Fails with "Image not found"

**Error**: `Failed to pull image: yourregistry.azurecr.io/orchestrator:latest`

**Fix:**
```bash
# Check if image exists in ACR
az acr repository list --name $ACR_NAME

# If missing, rebuild and push
docker build -t $ACR_LOGIN_SERVER/orchestrator:latest agents/orchestrator_agent
docker push $ACR_LOGIN_SERVER/orchestrator:latest
```

### Issue 2: Container App Crashes on Startup

**Error**: `Application failed to start` in logs

**Debug steps:**
1. Check environment variables are set correctly:
   ```bash
   az containerapp show --name orchestrator --resource-group azure-ai-agents \
     --query properties.template.containers[0].env
   ```

2. View startup logs:
   ```bash
   az containerapp logs show --name orchestrator --resource-group azure-ai-agents --tail 100
   ```

3. Common issues:
   - Missing `AZURE_OPENAI_ENDPOINT`
   - Invalid SQL connection string
   - Retriever URL not set for orchestrator

### Issue 3: A2A Communication Fails

**Error**: `Failed to call retriever agent`

**Fix:**
1. Verify retriever is running:
   ```bash
   az containerapp show --name retriever --resource-group azure-ai-agents \
     --query properties.runningStatus
   ```

2. Check RETRIEVER_URL in orchestrator:
   ```bash
   az containerapp show --name orchestrator --resource-group azure-ai-agents \
     --query "properties.template.containers[0].env[?name=='RETRIEVER_URL'].value" -o tsv
   ```

3. Test retriever directly:
   ```bash
   curl https://retriever-xxx.azurecontainerapps.io/.well-known/agent-card.json
   ```

### Issue 4: High Costs

**Problem**: Azure bill is higher than expected

**Investigate:**
```bash
# Check Container App scaling
az containerapp show --name orchestrator --resource-group azure-ai-agents \
  --query properties.template.scale

# Check Azure OpenAI usage
az monitor metrics list \
  --resource $(az cognitiveservices account show --name $OPENAI_NAME --resource-group azure-ai-agents --query id -o tsv) \
  --metric TotalTokens \
  --interval PT1H
```

**Optimize:**
1. Scale down Container Apps: `minReplicas: 0`
2. Use Azure SQL serverless (auto-pause)
3. Set Azure OpenAI quotas/alerts
4. Delete unused ACR images

---

## 📊 Performance Optimization

### Scaling Configuration

**Orchestrator (high traffic):**
```yaml
scale:
  minReplicas: 1  # Keep warm for fast response
  maxReplicas: 10
  rules:
  - name: http-rule
    http:
      metadata:
        concurrentRequests: '10'
```

**Retriever (moderate traffic):**
```yaml
scale:
  minReplicas: 0  # Scale to zero when idle
  maxReplicas: 5
  rules:
  - name: http-rule
    http:
      metadata:
        concurrentRequests: '20'
```

### Resource Limits

```yaml
resources:
  cpu: 0.5          # 0.5 vCPU
  memory: 1.0Gi     # 1 GB RAM
```

### Cold Start Optimization

1. Use `minReplicas: 1` for orchestrator (always warm)
2. Pre-load SQL connection pool on startup
3. Cache retriever URL in orchestrator
4. Use Application Insights for performance monitoring

---

## 🔐 Security Best Practices

1. **Use Managed Identity**: Replace API keys with managed identity
2. **Key Vault Integration**: Store secrets in Azure Key Vault
3. **Network Isolation**: Use virtual network integration
4. **HTTPS Only**: Enforce HTTPS for all ingress
5. **RBAC**: Grant minimal permissions to service principal
6. **Rotate Credentials**: Regularly rotate ACR passwords and API keys
7. **Audit Logs**: Enable diagnostic settings for all resources

---

## 📅 Maintenance Tasks

### Weekly
- Review Application Insights for errors
- Check cost management dashboard
- Delete old ACR images (> 7 days old)

### Monthly
- Review and optimize scaling rules
- Update base Docker images
- Rotate Azure OpenAI API keys
- Verify backup policies (SQL database)

### Quarterly
- Review security recommendations
- Update MAF framework and dependencies
- Load test system under peak conditions
- Review and optimize costs

---

## 🔗 Additional Resources

- [Azure Container Apps Docs](https://learn.microsoft.com/en-us/azure/container-apps/)
- [GitHub Actions for Azure](https://github.com/Azure/actions)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/)
- [Microsoft Agent Framework](https://microsoft.github.io/agent-framework/)

---

## 💬 Support

For deployment issues:
1. Check [GitHub Actions logs](https://github.com/abhimasum/AzureCloudAi/actions)
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. See [SETUP.md](SETUP.md) for initial configuration
4. Check [MIGRATION_STATUS.md](../MIGRATION_STATUS.md) for known issues
