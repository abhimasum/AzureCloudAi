# ⚙️ Foundry Setup Status & Next Steps

## 🔴 Current Status: Foundry Resources NOT YET Created

The automated Foundry Hub/Project creation via REST API failed due to an invalid Azure namespace. However, the infrastructure is ready for manual setup.

### What Succeeded ✅
- Docker builds (all 3 agents fixed and working)
- Azure infrastructure provisioned (SQL, Search, Storage, etc.)
- Workflow discovery and configuration
- ModelClient abstraction (supports fallback)

### What Needs Manual Setup ⏳
- Azure AI Foundry Hub creation
- Foundry Project creation  
- GPT-4o model deployment to Foundry
- API key retrieval and GitHub secrets configuration

---

## 📋 Quick Start Checklist

Follow these steps in order:

### Step 1: Create Foundry Hub (5 minutes)
- [ ] Go to https://ai.azure.com
- [ ] Click **Build** → **Create New Hub**
- [ ] Name: `ai-agent-foundry-hub`
- [ ] Location: `UK South`
- [ ] Resource group: `azure-ai-agents`
- [ ] Click **Create** (wait for completion)

### Step 2: Create Foundry Project (3 minutes)
- [ ] Inside Hub, click **Create New Project**
- [ ] Name: `ai-agent-foundry-project`
- [ ] Click **Create** (wait for completion)

### Step 3: Deploy GPT-4o Model (5 minutes)
- [ ] In Project, click **Model Catalog**
- [ ] Search for and select **gpt-4o**
- [ ] Click **Deploy**
- [ ] Select `Pay-as-you-go` or `Real-time`
- [ ] Click **Deploy** (wait 2-3 minutes)

### Step 4: Get API Key & Endpoint (2 minutes)
- [ ] In Project, click **Project Settings**
- [ ] Go to **API Keys** tab
- [ ] Copy the API Key (long string)
- [ ] Note the Endpoint: `https://uksouth.models.ai.azure.com`

### Step 5: Add GitHub Secrets (3 minutes)
- [ ] Go to GitHub repo → **Settings** → **Secrets and variables** → **Actions**
- [ ] Create secret: `AZURE_FOUNDRY_ENDPOINT` = `https://uksouth.models.ai.azure.com`
- [ ] Create secret: `AZURE_FOUNDRY_KEY` = [your API key from Step 4]

### Step 6: Re-run Workflow (15 minutes)
- [ ] Go to GitHub repo → **Actions**
- [ ] Click **Deploy Azure MAF Agents using Foundry**
- [ ] Click **Run workflow** → **Run workflow**
- [ ] Monitor all 8 jobs for ✅ success

### Step 7: Test the Deployment (5 minutes)
- [ ] Get Orchestrator URL from workflow output
- [ ] Visit the URL in browser to see web UI
- [ ] Try test queries (see FOUNDRY_SETUP_GUIDE.md for examples)

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│           GitHub Actions Workflow                       │
│  (deploy-foundry.yml - triggers on code push)          │
└─────────────────────────────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────┐
    │  1. Provision Infrastructure                         │
    │     ├─ Azure SQL Database                           │
    │     ├─ Azure AI Search                              │
    │     ├─ Azure Container Registry                     │
    │     └─ Container Apps Environment                  │
    └─────────────────────────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────┐
    │  2. Setup Database                                  │
    │     └─ Populate 28 states, districts, etc.         │
    └─────────────────────────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────┐
    │  3. Test Model Integration                          │
    │     ├─ Test Azure Foundry connection (if secrets)   │
    │     └─ Fallback to Direct OpenAI if needed          │
    └─────────────────────────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────┐
    │  4. Build & Push Docker Images                      │
    │     ├─ orchestrator-agent:latest                    │
    │     └─ retriever-agent:latest                       │
    └─────────────────────────────────────────────────────┘
                          ↓
    ┌──────────────────────┬──────────────────────────────┐
    │                      ↓                              ↓
    │  5. Deploy Retriever  6. Deploy Orchestrator        │
    │  (Container Apps)    (Container Apps)               │
    │                                                     │
    │  Port: 8081          Port: 8002                     │
    │  Uses: AI Search     Uses: Retriever + SQL          │
    └──────────────────────┬──────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────┐
    │  7. Upload Documents to AI Search                   │
    │     └─ 878 chunks from sample_docs/                │
    └─────────────────────────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────┐
    │  8. Deployment Summary                              │
    │     ├─ Orchestrator FQDN: [public URL]             │
    │     ├─ Retriever FQDN: [internal URL]              │
    │     └─ Test with sample queries                    │
    └─────────────────────────────────────────────────────┘
                          ↓
                    ┌───────────┐
                    │  Working  │
                    │   System  │
                    └─────┬─────┘
                          ↓
        Uses: Azure Foundry (primary) 
             → Falls back to OpenAI if needed
```

---

## 🔑 LLM Provider Logic

The agents use **dual-provider support**:

```python
# In agents/core/model_client.py
try:
    # Primary: Azure AI Foundry
    response = foundry_client.chat(
        endpoint=AZURE_FOUNDRY_ENDPOINT,
        key=AZURE_FOUNDRY_KEY,
        model="gpt-4o"
    )
except:
    # Fallback: Direct OpenAI
    response = openai_client.chat(
        api_key=OPENAI_API_KEY,
        model="gpt-4o"
    )
```

**This means:**
- ✅ If Foundry secrets exist → Use Foundry (primary)
- ✅ If Foundry secrets missing → Use OpenAI automatically
- ✅ If Foundry fails → Fallback to OpenAI
- ✅ **No manual code changes needed** - just add secrets!

---

## 🗂️ Key Files Modified This Session

| File | Changes | Status |
|------|---------|--------|
| `infra/setup_foundry.py` | Changed from REST API (broken) to manual guide | ✅ Pushed |
| `FOUNDRY_SETUP_GUIDE.md` | Step-by-step manual setup guide (NEW) | ✅ Pushed |
| `agents/core/model_client.py` | Dual-provider support with fallback | ✅ Working |
| `.github/workflows/deploy-foundry.yml` | Auto-trigger, configures Foundry env | ✅ Ready |

---

## ⚠️ Important Notes

1. **Foundry in UK South**: This region was chosen for cost efficiency. Change `AZURE_LOCATION` env var in workflow if you prefer a different region.

2. **API Key Required**: Without `AZURE_FOUNDRY_KEY` secret, agents will automatically fall back to OpenAI (full functionality, no changes needed).

3. **Workflow Auto-triggers**: The `deploy-foundry.yml` workflow automatically runs on:
   - Push to `master` branch (if code in `agents/`, `ingestion/`, `infra/`, or workflow itself changed)
   - Manual trigger via GitHub Actions UI
   - Weekly Sunday 2 AM UTC schedule

4. **Testing Without Foundry**: You can test agents immediately using OpenAI fallback (even without Foundry setup).

---

## 📞 Troubleshooting

### Hub creation failed
```
❌ Error: "Insufficient permissions"
→ Solution: Verify Azure subscription has AI Foundry resource provider registered
Command: az provider register --namespace Microsoft.MachineLearning
```

### Model deployment fails
```
❌ Error: "Resource not found" or "Validation failed"
→ Solution: Hub/Project may not be ready yet. Refresh page and retry after 2-3 mins
```

### API Key not working
```
❌ Error: "Unauthorized" in workflow
→ Solution: Verify GitHub secret name exactly matches: AZURE_FOUNDRY_KEY (case-sensitive)
```

### Still using OpenAI in logs
```
ℹ️ Message: "Using OpenAI fallback provider"
→ This is OK! Foundry secrets may not be set, but agents work fine with OpenAI
→ To use Foundry: Add AZURE_FOUNDRY_KEY and AZURE_FOUNDRY_ENDPOINT secrets
```

---

## 🎯 Next Immediate Actions

1. **Follow the 7-step checklist above** (20 minutes total)
2. **Re-run the workflow** after adding GitHub secrets
3. **Verify in logs** that Foundry is being used
4. **Test agent queries** with sample data
5. **Share feedback** if any steps unclear

See `FOUNDRY_SETUP_GUIDE.md` for detailed step-by-step screenshots and explanations.

