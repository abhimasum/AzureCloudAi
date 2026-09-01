# Architecture: Azure Multi-Agent System with MAF

**Three-tier microservices architecture** using **Microsoft Agent Framework (MAF)**, **Azure OpenAI**, **Azure SQL**, and **Azure AI Search** for agent-based Q&A.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     TIER 1: UI / Client Layer                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Browser (Client)                                             ││
│  │  • http://localhost:8002 (local dev)                          ││
│  │  • https://orchestrator-xxx.azurecontainerapps.io (prod)      ││
│  │  • Chat interface, session management                         ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP/REST
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│              TIER 2: Application / Agent Layer                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Orchestrator Agent (Port 8002)                               ││
│  │  • MAF Agent with sub_agents list                             ││
│  │  • Routes user queries to SQL or Retriever agents             ││
│  │  • Simple delegation (no graph workflows)                     ││
│  │  • FastAPI web server                                         ││
│  └──────────────────────┬────────────────────────────────────────┘│
│                         │ A2A Protocol (MAF built-in)             │
│  ┌──────────────────────┴────────────────────────────────────────┐│
│  │  SQL Agent (sub-agent, embedded)                              ││
│  │  • Queries Azure SQL Database                                 ││
│  │  • Returns geography index (states, districts)                ││
│  │  • All 28 states + 8 UTs embedded in instruction              ││
│  └──────────────────────┬────────────────────────────────────────┘│
│  ┌──────────────────────┴────────────────────────────────────────┐│
│  │  Retriever Agent (Port 8081)                                  ││
│  │  • A2A server (MAF framework)                                 ││
│  │  • search_knowledge_base() function                           ││
│  │  • Queries Azure AI Search (vector + semantic search)         ││
│  │  • Returns top 10 document passages                           ││
│  └──────────────────────┬────────────────────────────────────────┘│
└──────────────────────────┼───────────────────────────────────────┘
                           │ Azure SDKs (HTTPS)
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│           TIER 3: AI Backend / Azure Cloud Services              │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Azure OpenAI (GPT-4o)                                        ││
│  │  ┌──────────────────────────────────────────────────────────┐││
│  │  │ GPT-4o Deployment                                         │││
│  │  │ • Agent reasoning and response generation                 │││
│  │  │ • Context window: 128k tokens                             │││
│  │  │ • Temperature: 0.7                                        │││
│  │  └──────────────────────────────────────────────────────────┘││
│  │  ┌──────────────────────────────────────────────────────────┐││
│  │  │ Text Embedding Model (text-embedding-ada-002)            │││
│  │  │ • Converts text to 1536-dimension vectors                │││
│  │  │ • Used for semantic search in AI Search                  │││
│  │  └──────────────────────────────────────────────────────────┘││
│  └──────────────────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Azure AI Search (Vector + Semantic Search)                   ││
│  │  ┌──────────────────────────────────────────────────────────┐││
│  │  │ Documents Index                                           │││
│  │  │ • Vector search with HNSW algorithm                      │││
│  │  │ • Semantic ranking                                        │││
│  │  │ • Top-k retrieval (k=10)                                  │││
│  │  │ • Fields: id, content, title, embedding                   │││
│  │  └──────────────────────────────────────────────────────────┘││
│  └──────────────────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Azure SQL Database                                           ││
│  │  ┌──────────────────────────────────────────────────────────┐││
│  │  │ geography_index Database                                  │││
│  │  │ • countries table (1 row: India)                          │││
│  │  │ • states table (36 rows: 28 states + 8 UTs)               │││
│  │  │ • districts table (13 sample districts)                   │││
│  │  │ • Serverless tier (auto-pause when idle)                  │││
│  │  └──────────────────────────────────────────────────────────┘││
│  └──────────────────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Azure Blob Storage                                           ││
│  │  • Container: documents                                       ││
│  │  • Source files: india.md, states.md, districtandplace.md    ││
│  │  • Ingestion reads from here → indexes to AI Search          ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## Component 1: SQL Agent (Embedded Sub-Agent)

**Purpose**: Provide fast structured queries for geography index metadata.

**Technical Details:**

```
┌─────────────────────────────────────────────────────────────────┐
│  SQL Agent Internal Architecture                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: Orchestrator delegates query                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Query: "What is the capital of Maharashtra?"                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Agent instruction contains:                                   ││
│  │ • All 28 states with IDs and capitals embedded               ││
│  │ • Instruction to call get_state_info(state_name)             ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Connect to Azure SQL Database via pyodbc                      ││
│  │ • Connection string with ODBC Driver 18                       ││
│  │ • Execute: SELECT capital FROM states WHERE name=?           ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Return: {"state": "Maharashtra", "capital": "Mumbai"}        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Implementation:**
- **Functions**: `get_country_info()`, `get_state_info()`, `list_all_states()`
- **Database**: Azure SQL Database (Serverless tier)
- **Connector**: `pyodbc` with ODBC Driver 18 for SQL Server
- **Critical Design**: Functions NOT passed to Agent() constructor (MAF pattern), embedded in instruction instead
- **Data**: All 36 states/UTs with capitals hard-coded in instruction for fast reference

**File**: `agents/sql_agent/agent.py`

---

## Component 2: Retriever Agent (A2A Server)

**Purpose**: Perform semantic search over document corpus using Azure AI Search.

**Technical Details:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Retriever Agent Internal Architecture                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: Query via A2A protocol from Orchestrator                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ A2A Request:                                                  ││
│  │ {"method": "search_knowledge_base",                           ││
│  │  "params": {"query": "culture of Maharashtra"}}               ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ MAF Agent with search_knowledge_base() function               ││
│  │ • Uses azure-search-documents SDK                             ││
│  │ • SearchClient for vector + semantic search                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Query Azure AI Search Index                                   ││
│  │ • Convert query to embedding (Azure OpenAI)                   ││
│  │ • Vector search with top_k=10                                 ││
│  │ • Semantic ranking enabled                                    ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Return: Top 10 document passages                              ││
│  │ [{"content": "Maharashtra culture includes...",               ││
│  │   "title": "states.md", "score": 0.89}, ...]                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Implementation:**
- **Function**: `search_knowledge_base(query: str) -> list`
- **Search Service**: Azure AI Search (Basic tier)
- **Search Type**: Hybrid (vector + semantic)
- **Embedding Model**: text-embedding-ada-002 via Azure OpenAI
- **Parameters**: top_k=10, semantic_configuration enabled
- **Protocol**: A2A over HTTP (MAF framework handles this)

**File**: `agents/retriever_agent/agent.py`

---

## Component 3: Orchestrator Agent (Main Entry Point)

**Purpose**: Route user queries to appropriate specialist agents and synthesize responses.

**Technical Details:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Orchestrator Agent Internal Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: User query from web UI                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ HTTP POST /chat                                               ││
│  │ {"message": "Tell me about Maharashtra culture"}             ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ MAF Agent with sub_agents=[sql_agent, retriever_agent]       ││
│  │ • Instruction-based routing (NO graph workflows)              ││
│  │ • LLM decides which agent(s) to call                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Routing Logic (from instruction):                             ││
│  │ • General greetings → Direct response                         ││
│  │ • "List states" / "capital of X" → SQL Agent                 ││
│  │ • "culture" / "tell me about" → Retriever Agent              ││
│  │ • Complex queries → Both agents                               ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Delegate to sub-agents:                                       ││
│  │ • SQL Agent (embedded) → pyodbc query                         ││
│  │ • Retriever Agent (A2A) → HTTP call to port 8081             ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Synthesize final response with Azure OpenAI GPT-4o           ││
│  │ • Combine results from both agents                            ││
│  │ • Generate natural language answer                            ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Return to user: Comprehensive answer                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Implementation:**
- **Framework**: Microsoft Agent Framework (MAF) v1.16.0+
- **LLM**: Azure OpenAI GPT-4o (2024-08-06 version)
- **Sub-agents**: SQL Agent (embedded), Retriever Agent (remote via A2A)
- **Routing**: Instruction-based delegation (simple, no graph workflows per user requirement)
- **Web Server**: FastAPI on port 8002
- **Session Management**: In-memory chat history

**File**: `agents/orchestrator_agent/agent.py`, `agents/orchestrator_agent/main.py`

---

## Data Flow: Query Processing

### Example 1: "List all Indian states"

```
User Query → Orchestrator
              ↓
      Instruction matches "list states" pattern
              ↓
      Delegates to SQL Agent only
              ↓
      SQL Agent calls list_all_states()
              ↓
      Azure SQL query: SELECT name, capital FROM states
              ↓
      Returns 36 states with capitals
              ↓
      Orchestrator formats response
              ↓
      Returns to user: "Here are all 28 states and 8 UTs..."
```

### Example 2: "Tell me about Maharashtra culture"

```
User Query → Orchestrator
              ↓
      Instruction matches "culture" / "tell me about" pattern
              ↓
      Delegates to Retriever Agent only
              ↓
      Retriever calls search_knowledge_base("Maharashtra culture")
              ↓
      Azure AI Search vector search
              ↓
      Returns 10 passages from states.md
              ↓
      Orchestrator synthesizes with GPT-4o
              ↓
      Returns to user: "Maharashtra has a rich culture including..."
```

### Example 3: "What are the districts in Maharashtra?"

```
User Query → Orchestrator
              ↓
      Instruction determines need for both agents
              ↓
      Step 1: SQL Agent → get_state_info("Maharashtra") → state_id=14
      Step 2: Retriever → search_knowledge_base("Maharashtra districts")
              ↓
      Combine results from both
              ↓
      Orchestrator synthesizes comprehensive response
              ↓
      Returns to user: "Maharashtra (capital: Mumbai) has districts including..."
```

---

## Deployment Architecture

### Azure Container Apps Environment

```
┌─────────────────────────────────────────────────────────────────┐
│  Azure Container Apps Environment: ai-agents-env                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Container App: orchestrator                                  ││
│  │  • Image: yourregistry.azurecr.io/orchestrator:latest        ││
│  │  • Port: 8002                                                 ││
│  │  • Ingress: External (HTTPS)                                  ││
│  │  • Scale: 0-10 instances                                      ││
│  │  • CPU: 0.5, Memory: 1.0Gi                                    ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Container App: retriever                                     ││
│  │  • Image: yourregistry.azurecr.io/retriever:latest           ││
│  │  • Port: 8081                                                 ││
│  │  • Ingress: External (A2A communication)                      ││
│  │  • Scale: 0-5 instances                                       ││
│  │  • CPU: 0.25, Memory: 0.5Gi                                   ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Container App: ingestion (scheduled)                         ││
│  │  • Image: yourregistry.azurecr.io/ingestion:latest           ││
│  │  • Trigger: Manual / scheduled                                ││
│  │  • Scale: 0-1 instances                                       ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security & Authentication

1. **Managed Identity**: Container Apps use system-assigned managed identity
2. **Key Vault**: Sensitive credentials stored in Azure Key Vault (optional)
3. **RBAC**: Service-to-service auth via Azure AD
4. **Firewall Rules**: Azure SQL firewall restricts access to Azure services
5. **API Keys**: Azure OpenAI and AI Search use API keys (rotated regularly)

---

## Scalability & Performance

- **Auto-scaling**: Container Apps scale based on HTTP requests
- **Caching**: SQL results cached in orchestrator memory (30-minute TTL)
- **Rate Limiting**: Azure OpenAI quotas (10K tokens/minute)
- **Connection Pooling**: SQL connections pooled for efficiency
- **Async Processing**: Ingestion runs async, doesn't block queries

---

## Cost Optimization

| Service | Tier | Monthly Cost |
|---------|------|--------------|
| Azure OpenAI (GPT-4o) | Pay-per-use | ~$10-50 (light usage) |
| Azure SQL Database | Basic Serverless | ~$5 |
| Azure AI Search | Basic | ~$75 |
| Container Apps | Consumption | ~$20 (small workload) |
| Blob Storage | Standard LRS | <$1 |
| **Total** | | **~$110-150/month** |

---

## Monitoring & Observability

- **Application Insights**: Container Apps send logs and metrics
- **Log Analytics**: Centralized logging workspace
- **Alerts**: Azure Monitor alerts on errors, high latency
- **Metrics**: Request count, response time, token usage

---

## Future Enhancements

1. **Authentication**: Add Azure AD B2C for user auth
2. **Caching Layer**: Redis for query result caching
3. **Multi-tenancy**: Isolate data per user/organization
4. **Advanced Search**: Hybrid search with keyword + vector
5. **Voice Interface**: Azure Speech Services integration
