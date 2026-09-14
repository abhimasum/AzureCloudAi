# Azure AI Foundry Setup Guide

The automated REST API approach encountered namespace issues. Follow these **manual steps** to create your Foundry resources:

---

## Step 1: Create Azure AI Foundry Hub

1. Go to **https://ai.azure.com**
2. Click **"Build"** in the left menu
3. Click **"Create New Hub"**
4. Fill in details:
   - **Hub name**: `ai-agent-foundry-hub`
   - **Subscription**: Select your Azure subscription
   - **Location**: `UK South` (or `uksouth` - must match workflow env var `AZURE_LOCATION`)
   - **Resource group**: `azure-ai-agents`
5. Click **"Create"** and wait 2-3 minutes for it to be ready

---

## Step 2: Create Foundry Project

1. After Hub is created, you'll be in the Hub dashboard
2. Click **"Create New Project"** (or **"Create a new project"** button)
3. Fill in details:
   - **Project name**: `ai-agent-foundry-project`
   - **Description**: (optional) `AI Agent Foundry Project`
4. Click **"Create"** and wait for it to be ready (~1 minute)

---

## Step 3: Deploy GPT-4o Model

1. Inside the Project, click **"Model Catalog"** (or search for models)
2. Search for **"gpt-4o"**
3. Click on **"gpt-4o"** result
4. Click **"Deploy"** button
5. Select deployment type:
   - **Deployment type**: `Pay-as-you-go` (or `Real-time`for low latency)
   - **Deployment name**: `gpt-4o` (default)
6. Click **"Deploy"** and wait 2-3 minutes

---

## Step 4: Get API Key & Endpoint

1. In Project dashboard, click **"Project Settings"** (bottom left)
2. Go to **"API Keys"** tab
3. Click **"Create New API Key"** or copy existing key
4. Copy the **API Key** (long string)
5. **Note the Endpoint**: Should be something like:
   ```
   https://uksouth.models.ai.azure.com
   ```
   (Region must match your Hub location)

---

## Step 5: Add Secrets to GitHub

1. Go to your GitHub repository: **https://github.com/abhimasum/AzureCloudAi**
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**

### Create Secret 1: AZURE_FOUNDRY_ENDPOINT
- **Name**: `AZURE_FOUNDRY_ENDPOINT`
- **Value**: `https://uksouth.models.ai.azure.com`
- Click **"Add secret"**

### Create Secret 2: AZURE_FOUNDRY_KEY
- **Name**: `AZURE_FOUNDRY_KEY`
- **Value**: [Paste the API key from Step 4]
- Click **"Add secret"**

---

## Step 6: Trigger Deployment Workflow

1. Go to your GitHub repository
2. Click **"Actions"** tab
3. Click **"Deploy Azure MAF Agents using Foundry"** workflow
4. Click **"Run workflow"** button
5. Select branch: `master`
6. Click **"Run workflow"**
7. Monitor the run:
   - Watch for ✅ checkmarks on each job
   - `provision-infrastructure` ✓
   - `setup-database` ✓
   - `test-model-integration` ✓
   - `build-and-push-images` ✓
   - `deploy-retriever` ✓
   - `deploy-orchestrator` ✓
   - `upload-documents` ✓
   - `deployment-summary` ✓

---

## Step 7: Test the Agents

Once deployment completes:

1. Get the **Orchestrator URL** from the `deployment-summary` job output
2. Send test queries:

```bash
# Via curl
curl -X POST https://<orchestrator-url>/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about India"}'

# Or visit the web UI (if available)
https://<orchestrator-url>
```

Test queries to try:
- "Tell me about India" (RAG search)
- "What are the 28 states of India?" (SQL query)
- "Culture of Bangalore" (Vector search)

---

## Step 8: Verify Foundry is Being Used

Check the workflow logs:
1. Click on the completed workflow run
2. Go to **"test-model-integration"** job
3. Look for logs showing:
   - ✓ `Using Foundry endpoint...`
   - ✓ `Model response received from Foundry`

Or check agent logs:
```bash
# SSH into Container App and check logs
az containerapp logs show --name orchestrator-agent \
  --resource-group azure-ai-agents \
  --tail 50
```

---

## Troubleshooting

### Hub creation failed
- Verify subscription has AI Foundry access
- Check resource group `azure-ai-agents` exists
- Try different location if `uksouth` unavailable

### Model deployment failed
- Ensure Hub and Project are fully created (refresh page)
- Check quota limits in your subscription
- Try `gpt-4o-mini` if `gpt-4o` unavailable

### API Key not working
- Verify you copied the full key (no extra spaces)
- Check key hasn't expired (regenerate if needed)
- Verify secret was added correctly in GitHub

### Workflow still using OpenAI fallback
- Verify `AZURE_FOUNDRY_KEY` and `AZURE_FOUNDRY_ENDPOINT` secrets are present
- Re-run workflow after adding secrets
- Check agent logs for error messages

### Can't access deployed agents
- Wait 2-3 minutes for Container Apps to fully start
- Check Container App status in Azure Portal
- Verify networking rules allow your IP

---

## References

- [Azure AI Foundry Documentation](https://learn.microsoft.com/en-us/azure/ai-studio/)
- [Model Catalog](https://learn.microsoft.com/en-us/azure/ai-studio/how-to/model-catalog)
- [Getting Started with Foundry](https://learn.microsoft.com/en-us/azure/ai-studio/what-is-ai-studio)

