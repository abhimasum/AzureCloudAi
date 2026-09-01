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

### Prerequisites
- Azure account (abhimausm2@gmail.com)
- Azure CLI installed
- Python 3.11+
- Git

### 1. Setup Azure Resources
```bash
# Login to Azure
az login

# Run setup script (creates all resources)
bash infra/setup_azure.sh
```

### 2. Configure Secrets
```bash
# Copy credentials from setup script output
cp .env.example .env
# Edit .env with your Azure credentials
```

### 3. Test Locally
```bash
pip install -r requirements.txt
python agents/orchestrator_agent/main.py
```

### 4. Deploy to Azure
```bash
# Setup GitHub secrets (one-time)
# See docs/SETUP.md for GitHub secrets configuration

# Deploy via push
git add -A
git commit -m "Deploy agents"
git push origin master
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
