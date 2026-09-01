# Azure Cloud AI Multi-Agent System

**Multi-agent Q&A system** for Indian geography using **Microsoft Agent Framework (MAF)**, **Azure OpenAI (GPT-4o)**, **Azure SQL Database**, and **Azure AI Search** with vector RAG.

---

## 🏗️ Architecture

```
User Query → Orchestrator Agent 
              ├─→ SQL Agent (Azure SQL: countries/states/districts index)
              └─→ Retriever Agent (Azure AI Search: RAG over documents)
```

### Azure Services Stack

| Service | Role | Why |
|---------|------|-----|
| **Microsoft Agent Framework (MAF)** | Agent orchestration | Simple sub-agent delegation (v1.16.0+) |
| **Azure OpenAI GPT-4o** | LLM reasoning | Powers all agent responses |
| **Azure SQL Database** | Geography index | Fast structured queries (28 states + UTs) |
| **Azure AI Search** | Vector RAG | Semantic search over documents |
| **Azure Blob Storage** | Document storage | Source files for ingestion |
| **Azure Container Apps** | Agent hosting | Serverless container deployment |
| **Azure Container Registry** | Image storage | Docker images for agents |
| **GitHub Actions** | CI/CD | Automated build & deploy |

---

## ✅ Features

- **3 Specialized Agents**: SQL Agent (index), Retriever Agent (RAG), Orchestrator (routing)
- **Simple Delegation**: No graph workflows - clean agent routing like GCP version
- **28 Indian States**: All states + union territories with capitals embedded
- **A2A Protocol**: Agent-to-agent communication built into MAF
- **Automated CI/CD**: Push to deploy via GitHub Actions

---

## 🚀 Quick Start

### Automated Deployment (Recommended)

The easiest way to deploy is via GitHub Actions - it automatically creates all Azure resources.

**3 Simple Steps:**

1. **Create Service Principal**
   ```bash
   az login
   SUBSCRIPTION_ID=$(az account show --query id -o tsv)
   az ad sp create-for-rbac \
     --name "github-actions-azureai" \
     --role "Contributor" \
     --scopes "/subscriptions/$SUBSCRIPTION_ID" \
     --sdk-auth
   # Copy the entire JSON output
   ```

2. **Add GitHub Secrets**
   - Go to: `https://github.com/abhimasum/AzureCloudAi/settings/secrets/actions`
   - Add `AZURE_CREDENTIALS` (JSON from step 1)
   - Add `AZURE_SQL_PASSWORD` (choose a strong password)

3. **Deploy**
   ```bash
   git commit --allow-empty -m "Deploy to Azure"
   git push origin master
   ```

**That's it!** GitHub Actions will:
- ✅ Create all Azure resources (SQL, OpenAI, AI Search, Storage, ACR, Container Apps)
- ✅ Setup database with 36 states/UTs
- ✅ Build and deploy all agents
- ✅ Give you the deployment URL

**See full instructions:** [docs/SETUP.md](docs/SETUP.md#-part-0-get-github-secrets-do-this-first)

---

### Manual Setup (Alternative)

If you prefer manual control:

```bash
# Login to Azure
az login

# Run setup script
bash infra/setup_azure.sh
```

---

## 📖 Documentation

- **[Setup Guide](docs/SETUP.md)** - Step-by-step Azure setup with your account
- **[Architecture](docs/ARCHITECTURE.md)** - System design and data flow
- **[Deployment](docs/DEPLOYMENT.md)** - Container Apps deployment & GitHub Actions

---

## 🔍 Example Queries

```
"Tell me about India"                    → General info (Retriever)
"What is the capital of Maharashtra?"    → SQL query
"List all states"                        → SQL index
"What is the culture of Maharashtra?"    → RAG search
"Tell me about Mumbai district"          → SQL + RAG combination
```

---

## 📦 Project Structure

```
AzureCloudAi/
├── agents/
│   ├── sql_agent/          # Azure SQL queries
│   ├── retriever_agent/    # Azure AI Search RAG
│   └── orchestrator_agent/ # Main routing agent
├── ingestion/              # Document indexing service
├── infra/                  # Setup scripts
├── data/sample_docs/       # Sample geography documents
└── docs/                   # Comprehensive guides
```

---

## 🎯 Migration from GCP

This project replicates the **GoogleCloudAi** architecture using Azure-native services:

| GCP Service | Azure Equivalent |
|-------------|-----------------|
| Google ADK | Microsoft Agent Framework |
| Vertex AI Gemini | Azure OpenAI GPT-4o |
| BigQuery | Azure SQL Database |
| Vertex AI RAG Engine | Azure AI Search |
| Cloud Run | Azure Container Apps |
| Artifact Registry | Azure Container Registry |
| Cloud Storage | Azure Blob Storage |

**Key Design**: Same simple delegation pattern - no graph workflows, clean routing logic.

---

## 💰 Cost Estimate

- **Azure SQL Basic**: ~$5/month (serverless)
- **Azure OpenAI**: Pay-per-token (~$10-50/month light usage)
- **AI Search Basic**: ~$75/month
- **Container Apps**: Free tier available, ~$20/month small workload
- **Storage**: <$1/month for small datasets

**Total**: ~$100-150/month for dev/test environment

---

## 🧹 Cleanup

To delete all resources:
```bash
az group delete --name azure-ai-agents --yes
```

---

## 📝 License

MIT License - see GoogleCloudAi project for details.
