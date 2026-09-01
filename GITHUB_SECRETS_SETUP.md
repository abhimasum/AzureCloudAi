# GitHub Secrets Setup for Azure Deployment

This file lists all required GitHub secrets for the CI/CD pipeline. The pipeline will **automatically create all Azure resources** - you just need to provide credentials.

---

## 🔑 Required Secrets

Add these secrets at: `https://github.com/abhimasum/AzureCloudAi/settings/secrets/actions`

### 1. Azure Service Principal (for GitHub Actions login)

**Secret Name:** `AZURE_CREDENTIALS`

**How to get:**
```bash
# Get your subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Create service principal
az ad sp create-for-rbac \
  --name "github-actions-azureai" \
  --role "Contributor" \
  --scopes "/subscriptions/$SUBSCRIPTION_ID" \
  --sdk-auth

# Copy the ENTIRE JSON output to AZURE_CREDENTIALS secret
```

**Value format:**
```json
{
  "clientId": "xxx",
  "clientSecret": "xxx",
  "subscriptionId": "xxx",
  "tenantId": "xxx",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

---

### 2. Azure SQL Password

**Secret Name:** `AZURE_SQL_PASSWORD`

**Value:** Choose a strong password (min 12 characters, mix of upper/lower/numbers/symbols)

**Example:** `MySecureP@ssw0rd2024!`

**Note:** This will be used when creating the SQL Server for the first time.

---

### 3. Azure OpenAI Credentials

**Secret Name:** `AZURE_OPENAI_ENDPOINT`  
**Value:** Will be auto-created by pipeline, or use existing: `https://your-openai.openai.azure.com/`

**Secret Name:** `AZURE_OPENAI_API_KEY`  
**Value:** Will be auto-created by pipeline, or get from existing OpenAI resource:
```bash
az cognitiveservices account keys list \
  --name YOUR_OPENAI_NAME \
  --resource-group azure-ai-agents \
  --query key1 -o tsv
```

---

### 4. Azure AI Search Credentials

**Secret Name:** `AZURE_SEARCH_ENDPOINT`  
**Value:** Will be auto-created by pipeline, or use existing: `https://your-search.search.windows.net`

**Secret Name:** `AZURE_SEARCH_KEY`  
**Value:** Will be auto-created by pipeline, or get from existing Search service:
```bash
az search admin-key show \
  --resource-group azure-ai-agents \
  --service-name YOUR_SEARCH_NAME \
  --query primaryKey -o tsv
```

---

## 📝 Optional Secrets (Pipeline uses defaults if not provided)

| Secret Name | Default Value | Purpose |
|-------------|---------------|---------|
| `AZURE_RESOURCE_GROUP` | `azure-ai-agents` | Resource group name |
| `AZURE_LOCATION` | `eastus` | Azure region |
| `ACR_NAME` | `aiagentsacr` | Container registry name |
| `CONTAINER_ENV` | `ai-agents-env` | Container Apps environment |
| `AZURE_SQL_SERVER_NAME` | Auto-generated | SQL Server name |
| `AZURE_OPENAI_NAME` | `ai-agents-openai` | OpenAI resource name |
| `AZURE_SEARCH_NAME` | `ai-agents-search` | AI Search service name |
| `AZURE_STORAGE_NAME` | Auto-generated | Storage account name |

---

## ⚡ Quick Setup (Minimum Required)

**For first-time setup**, you only need these 2 secrets:

1. **`AZURE_CREDENTIALS`** - Service principal JSON from `az ad sp create-for-rbac`
2. **`AZURE_SQL_PASSWORD`** - Your chosen SQL password

The pipeline will:
- ✅ Create all Azure resources automatically
- ✅ Get OpenAI and Search keys automatically
- ✅ Setup SQL database with schema
- ✅ Deploy all Container Apps

**After first deployment**, get the auto-generated credentials and add them as secrets for subsequent deploys:

```bash
# Get OpenAI credentials
az cognitiveservices account show --name ai-agents-openai --resource-group azure-ai-agents --query properties.endpoint -o tsv
az cognitiveservices account keys list --name ai-agents-openai --resource-group azure-ai-agents --query key1 -o tsv

# Get AI Search credentials
az search admin-key show --resource-group azure-ai-agents --service-name ai-agents-search --query primaryKey -o tsv
```

---

## 🚀 Deploy After Setup

Once secrets are configured:

```bash
git add -A
git commit -m "Deploy to Azure"
git push origin master
```

The workflow will:
1. ✅ Check if resources exist, create if missing
2. ✅ Setup SQL database with 36 states/UTs
3. ✅ Build and push Docker images
4. ✅ Deploy Container Apps
5. ✅ Upload sample documents

**Deployment time:** ~10-15 minutes (first run with resource creation)  
**Subsequent deploys:** ~5-8 minutes (only updates Container Apps)

---

## 🔧 Verify Secrets Setup

After adding secrets, run this workflow manually to test:

1. Go to: `https://github.com/abhimasum/AzureCloudAi/actions`
2. Select "Deploy Azure MAF Agents"
3. Click "Run workflow"
4. Choose branch: `master`
5. Click "Run workflow"

Check the logs for any missing secrets or errors.

---

## 🆘 Troubleshooting

### "Error: AZURE_CREDENTIALS secret not found"
→ Make sure you created the service principal with `--sdk-auth` flag and copied the ENTIRE JSON output.

### "Error: SQL authentication failed"
→ Check that `AZURE_SQL_PASSWORD` meets complexity requirements (min 12 chars, mixed case, numbers, symbols).

### "Error: Service principal doesn't have permissions"
→ The service principal needs `Contributor` role on the subscription or resource group:
```bash
az role assignment create \
  --assignee YOUR_SP_APP_ID \
  --role Contributor \
  --scope /subscriptions/YOUR_SUBSCRIPTION_ID
```

### "Error: Resource names must be globally unique"
→ Modify the default names using optional secrets (e.g., change `ACR_NAME` from `aiagentsacr` to something unique like `aiagentsacr12345`).

---

## 📚 Additional Resources

- [Azure Service Principal Docs](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure)
- [GitHub Secrets Management](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
