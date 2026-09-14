# Azure AI Foundry Migration Guide

This guide explains how to migrate from Direct OpenAI to **Azure AI Foundry** for multi-model support and better cost management.

## Why Azure AI Foundry?

✅ **Cost Optimization**: Use Visual Studio subscription credits (~$50/month free)  
✅ **Multi-Model Support**: Switch between GPT-4o, Claude, Meta models without code changes  
✅ **Better Governance**: Azure-native monitoring, audit logs, cost controls  
✅ **Redundancy**: Failover between models if one is unavailable  
✅ **Future-Proof**: Ready for new models as they become available  

## Current Architecture

Currently, the system uses **Direct OpenAI API** (gpt-4o via personal API key):

```
Your App → Direct OpenAI API (OPENAI_API_KEY) → OpenAI Models
```

## Target Architecture with Foundry

```
Your App → Azure AI Foundry → Multiple Model Providers
                              ├─ GPT-4o (Default)
                              ├─ Claude 3.5 Sonnet
                              ├─ Meta Llama
                              └─ Custom Fine-tuned Models
```

## Migration Steps

### Step 1: Create Azure AI Foundry Hub & Project

```bash
# 1. Open Azure Portal
# 2. Search for "Azure AI Foundry" or go to https://ai.azure.com
# 3. Click "Create Hub"
# 4. Select your subscription and resource group (azure-ai-agents)
# 5. Configure:
#    - Hub Name: ai-agent-foundry-hub
#    - Location: UK South (same as existing resources)
# 6. Click "Create"

# Wait 5-10 minutes for provisioning...

# 7. Once Hub is created:
#    - Click "+ Create Project"
#    - Name: ai-agent-foundry-project
#    - Location: UK South
# 8. Click "Create"
```

### Step 2: Deploy Models in Foundry

After Hub & Project are created:

```bash
# In Azure AI Foundry:
# 1. Go to "Model Catalog"
# 2. For each model you want:
#    - Click model name (e.g., "gpt-4o")
#    - Click "Deploy"
#    - Configure:
#      - Deployment Name: gpt-4o (keep it simple)
#      - Model Version: Latest
#      - Deployment Type: Standard
#    - Click "Deploy"
# 3. Wait for deployment to complete (shows green checkmark)

# Models to deploy:
# - gpt-4o (default, replaces current)
# - claude-3-5-sonnet (optional, for experimentation)
```

### Step 3: Get Connection Details

In Azure AI Foundry:

```bash
# 1. Go to "Project Settings" → "Keys & Endpoints"
# 2. Copy:
#    - API Endpoint: https://xxx.models.ai.azure.com (save as AZURE_FOUNDRY_ENDPOINT)
#    - API Key: xxxxxxxx (save as AZURE_FOUNDRY_KEY secret)
# 3. Note the deployment names (should be "gpt-4o", "claude-3-5-sonnet")
```

### Step 4: Add GitHub Secrets

```bash
# 1. Go to your GitHub repository
# 2. Settings → Secrets and variables → Actions
# 3. Click "New repository secret"
# 4. Add:
#    - Name: AZURE_FOUNDRY_ENDPOINT
#      Value: https://xxx.models.ai.azure.com
#    - Name: AZURE_FOUNDRY_KEY
#      Value: [API key from Foundry]
```

### Step 5: Update Deployment Configuration

Edit `.github/workflows/deploy.yml`:

```yaml
env:
  # Change these to enable Foundry:
  MODEL_NAME: "gpt-4o"           # or "claude-3-5-sonnet"
  USE_AZURE_FOUNDRY: "true"      # Enable Foundry (was "false")
  
  # For Foundry deployments:
  AZURE_FOUNDRY_ENDPOINT: ${{ secrets.AZURE_FOUNDRY_ENDPOINT }}
  AZURE_FOUNDRY_KEY: ${{ secrets.AZURE_FOUNDRY_KEY }}
```

### Step 6: Update Container Deployments

The orchestrator and retriever deployments automatically pick up these variables. You can also add to the deployment step:

```yaml
# In deploy-orchestrator and deploy-retriever sections:
--set-env-vars \
  OPENAI_API_KEY=secretref:openai-api-key \
  MODEL_NAME=${{ env.MODEL_NAME }} \
  USE_AZURE_FOUNDRY=${{ env.USE_AZURE_FOUNDRY }} \
  AZURE_FOUNDRY_ENDPOINT=${{ env.AZURE_FOUNDRY_ENDPOINT }} \
  AZURE_FOUNDRY_KEY=secretref:foundry-key \
```

### Step 7: Deploy & Test

```bash
# 1. Commit and push changes:
git add .github/workflows/deploy.yml
git commit -m "Enable Azure AI Foundry support"
git push origin master

# 2. GitHub Actions will trigger automatically
# 3. Wait for deployment to complete
# 4. Test in chat:
#    - "List 28 states" (SQL query)
#    - "Culture of Maharashtra" (RAG query)
#    - "Hello" (direct response)
```

## Switching Between Models

To switch from gpt-4o to claude-3-5-sonnet:

```yaml
env:
  MODEL_NAME: "claude-3-5-sonnet"   # Change this
  USE_AZURE_FOUNDRY: "true"
  
  # Make sure Claude is deployed in Foundry
```

Then push - deployment updates automatically!

## Fallback Strategy

If USE_AZURE_FOUNDRY is disabled or Foundry is unavailable:

```
USE_AZURE_FOUNDRY=false  →  Falls back to Direct OpenAI (OPENAI_API_KEY)
```

This ensures your system works even if Foundry has issues.

## Cost Comparison

### Current (Direct OpenAI)
- GPT-4o: $0.03/1K input tokens, $0.06/1K output tokens
- Monthly estimate: $20-50 (depending on usage)

### With Azure Foundry + VS Subscription
- VS Subscription credit: $50/month free
- Most models included in credit
- Only pay if exceeding monthly credit

**Savings**: Potentially free for light-to-moderate usage!

## Monitoring & Costs

In Azure AI Foundry:

```
1. Go to "Deployments"
2. Click your deployment (e.g., "gpt-4o")
3. See:
   - Token usage
   - Cost tracking
   - Performance metrics
4. Alerts available for quota warnings
```

## Troubleshooting

### Foundry returns 400 error
- ❌ Model not deployed
- ✅ Solution: Deploy model in Foundry catalog

### Rate limiting
- ❌ Quota exceeded
- ✅ Solution: Scale up deployment in Foundry

### Model mismatch
- ❌ MODEL_NAME doesn't match deployed model name
- ✅ Solution: Check deployment names in Foundry match MODEL_NAME env var

## Rolling Back to Direct OpenAI

If you encounter issues:

```yaml
env:
  USE_AZURE_FOUNDRY: "false"    # Disable Foundry
  
  # System automatically uses OPENAI_API_KEY
```

Push and redeploy - no Foundry dependencies needed!

## Next Steps

1. ✅ Create Foundry Hub & Project
2. ✅ Deploy models (gpt-4o minimum)
3. ✅ Add GitHub secrets
4. ✅ Update deploy.yml
5. ✅ Deploy and test
6. 🟡 Monitor costs and usage
7. 🟡 Optional: Deploy additional models (Claude, Llama, etc.)

## Documentation References

- [Azure AI Foundry Docs](https://learn.microsoft.com/en-us/azure/ai-studio/)
- [Model Catalog](https://ai.azure.com/explore/models)
- [Pricing](https://azure.microsoft.com/en-us/pricing/details/ai-studio/)
- [API Reference](https://learn.microsoft.com/en-us/python/api/azure-ai-inference/)
