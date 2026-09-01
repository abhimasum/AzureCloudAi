# Architecture: Google AI Agent System

This is a **three-tier microservices architecture** teaching you how to build AI agents that work together via the **A2A (Agent-to-Agent) protocol**. Each tier has distinct responsibilities, enabling scalability and separation of concerns.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     TIER 1: UI / Web Layer                       │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Browser (Client)                                             ││
│  │  • http://localhost:8002 (local dev)                          ││
│  │  • https://orchestrator-agent-xxx.run.app (production)        ││
│  │  • Chat interface, session management                         ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP/REST
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│              TIER 2: Application / Agent Layer                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Orchestrator Agent (Port 8002)                               ││
│  │  • FastAPI Web Server                                         ││
│  │  • Routes user queries to the right agent                     ││
│  │  • Uses RemoteA2aAgent to call Retriever                      ││
│  │  • Synthesizes responses with Gemini LLM                      ││
│  └──────────────────────────┬───────────────────────────────────┘│
│                             │ A2A Protocol (JSON-RPC over HTTP)   │
│  ┌──────────────────────────┴───────────────────────────────────┐│
│  │  Retriever Agent (Port 8081)                                  ││
│  │  • Starlette A2A Server                                       ││
│  │  • Exposes agent card (.well-known/agent-card.json)           ││
│  │  • Single tool: VertexAiRagRetrieval                          ││
│  │  • Queries RAG corpus for grounding                           ││
│  └──────────────────────────┬───────────────────────────────────┘│
└──────────────────────────────┼───────────────────────────────────┘
                               │ Vertex AI API (gRPC/REST)
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│           TIER 3: AI Backend / Google Cloud Services             │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Vertex AI (Managed LLM + RAG Engine)                         ││
│  │  ┌──────────────────────────────────────────────────────────┐││
│  │  │ Gemini 2.0 Flash LLM                                      │││
│  │  │ • generate_content(): High-speed inference                │││
│  │  │ • Token counting, embedding generation                    │││
│  │  └──────────────────────────────────────────────────────────┘││
│  │  ┌──────────────────────────────────────────────────────────┐││
│  │  │ RAG Engine (Retrieval-Augmented Generation)              │││
│  │  │ • Semantic search in ingested corpus                      │││
│  │  │ • Chunk retrieval (typically top-k=10)                    │││
│  │  │ • Embedding-based similarity                              │││
│  │  └──────────────────────────────────────────────────────────┘││
│  │  ┌──────────────────────────────────────────────────────────┐││
│  │  │ Embeddings API (text-embedding-005)                      │││
│  │  │ • Converts text to 768-dimension vectors                  │││
│  │  │ • Used for semantic search and chunking                   │││
│  │  └──────────────────────────────────────────────────────────┘││
│  └──────────────────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Data Layer                                                   ││
│  │  • RAG Corpus (projects/1073291557100/locations/europe-west4/ragCorpora/4611686018427387904)
│  │  • Cloud Storage Bucket (gs://agenticaigcplearn-adk-docs/)    ││
│  │  • Cloud Scheduler (Cron: re-ingest documents daily)         ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Retriever Agent (A2A Server)

**Purpose**: A single-responsibility agent that retrieves information from the knowledge base. It runs on port 8081 locally.

**Technical Details:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Retriever Agent Internal Architecture                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input: User Query (via A2A RPC call)                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. Query received via HTTP POST /                            ││
│  │    {                                                          ││
│  │      "jsonrpc": "2.0",                                        ││
│  │      "method": "retrieve",                                    ││
│  │      "params": {"query": "What is RAG Engine?"},              ││
│  │      "id": 1                                                  ││
│  │    }                                                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 2. Google ADK processes the request                           ││
│  │    • Converts query to embedding (text-embedding-005)         ││
│  │    • Calls VertexAiRagRetrieval tool                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 3. RAG Engine retrieves relevant chunks                       ││
│  │    • Queries corpus with semantic search                      ││
│  │    • Returns top-k chunks (usually 10)                        ││
│  │    • Each chunk: document name, text, score                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 4. Response sent back to orchestrator                         ││
│  │    {                                                          ││
│  │      "jsonrpc": "2.0",                                        ││
│  │      "result": [                                              ││
│  │        {                                                      ││
│  │          "text": "RAG Engine is a Vertex AI...",              ││
│  │          "document": "rag_engine_overview.md",                ││
│  │          "score": 0.87                                        ││
│  │        },                                                      ││
│  │        ...                                                    ││
│  │      ],                                                       ││
│  │      "id": 1                                                  ││
│  │    }                                                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                          ↓                                       │
│  Output: Retrieved Chunks (sent to Orchestrator)                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Code Structure

**File**: [`agents/retriever_agent/agent.py`](../agents/retriever_agent/agent.py)
- Defines the ADK `Agent` with `VertexAiRagRetrieval` tool
- Tool connects to: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `RAG_CORPUS`

**File**: [`agents/retriever_agent/a2a_app.py`](../agents/retriever_agent/a2a_app.py)
- Wraps agent with `to_a2a()` function
- Handles A2A protocol (JSON-RPC 2.0)
- Exposes two endpoints:
  - `GET /.well-known/agent-card.json` → Describes capabilities
  - `POST /` → Executes RPC calls

### Key Implementation Details

**A2A Protocol Endpoint:**
```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Convert agent to A2A server
a2a_app = to_a2a(
    root_agent=root_agent,
    host=HOST,           # "localhost" (local) or FQDN (cloud)
    port=PORT             # 8081
)

# Server automatically:
# • Implements JSON-RPC 2.0 protocol at POST /
# • Serves agent card at GET /.well-known/agent-card.json
# • Handles request/response serialization
```

**Agent Card (Discovery Document):**
```json
{
  "name": "retriever-agent",
  "description": "RAG corpus retrieval agent",
  "version": "1.0.0",
  "url": "http://localhost:8081/",
  "tools": [
    {
      "name": "retrieve",
      "description": "Search the knowledge base for relevant information",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"}
        }
      }
    }
  ]
}
```

### Debugging/Verification Commands

```powershell
# 1. Check if agent is running
curl http://localhost:8081/

# 2. Get agent card (capabilities)
curl http://localhost:8081/.well-known/agent-card.json

# 3. Test a retrieval (A2A JSON-RPC call)
$query = @{
    jsonrpc = "2.0"
    method = "retrieve"
    params = @{ query = "What is RAG Engine?" }
    id = 1
} | ConvertTo-Json

curl -Method POST `
  -Uri http://localhost:8081/ `
  -ContentType "application/json" `
  -Body $query

# 4. Check if RAG corpus is accessible
gcloud ai documents corpus list --location=europe-west4

# 5. View environment variables
Get-ChildItem env: | Where-Object { $_.Name -like "GOOGLE*" -or $_.Name -like "RAG*" }
```

### Why A2A Instead of REST API?

| Feature | A2A Protocol | Custom REST API |
|---|---|---|
| **Discovery** | Automatic agent card | Manual documentation |
| **Interoperability** | Standard Google format | Custom implementation |
| **Type Safety** | Schema-driven | Manual validation |
| **Code Generation** | Auto-generated clients | Manual coding |
| **Error Handling** | Standardized | Custom per endpoint |

---

## Component 2: Orchestrator Agent (Web Server)

**Purpose**: The main entry point for users. Receives queries, delegates to Retriever via A2A, and synthesizes final responses with the LLM.

**Technical Details:**

```
┌────────────────────────────────────────────────────────────────┐
│  Orchestrator Agent Request-Response Flow                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. User types query in browser                               │
│     "What is A2A Protocol?"                                   │
│     ↓                                                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Browser sends: POST /message                             │ │
│  │ Body: { "message": "What is A2A Protocol?" }             │ │
│  └──────────────────────────────────────────────────────────┘ │
│     ↓                                                          │
│  2. FastAPI receives request → passes to ADK                 │
│     ↓                                                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ADK Agent processes:                                      │ │
│  │ • Prompt: "You are helpful assistant. User asked..."    │ │
│  │ • Available tools: RemoteA2aAgent (retrieve)              │ │
│  │ • LLM decides: "I need to retrieve from knowledge base"  │ │
│  │ • Calls retrieve("What is A2A Protocol?")                │ │
│  └──────────────────────────────────────────────────────────┘ │
│     ↓                                                          │
│  3. RemoteA2aAgent calls Retriever via HTTP                  │
│     ┌──────────────────────────────────────────────────────┐ │
│     │ POST http://localhost:8081/                          │ │
│     │ {                                                    │ │
│     │   "jsonrpc": "2.0",                                  │ │
│     │   "method": "retrieve",                              │ │
│     │   "params": { "query": "A2A Protocol" },             │ │
│     │   "id": 1                                            │ │
│     │ }                                                    │ │
│     └──────────────────────────────────────────────────────┘ │
│     ↓                                                          │
│  4. Retriever responds with chunks                           │
│     ┌──────────────────────────────────────────────────────┐ │
│     │ Response: [                                           │ │
│     │   {                                                  │ │
│     │     "text": "A2A is Agent-to-Agent protocol...",      │ │
│     │     "score": 0.92                                    │ │
│     │   },                                                 │ │
│     │   ...                                                │ │
│     │ ]                                                    │ │
│     └──────────────────────────────────────────────────────┘ │
│     ↓                                                          │
│  5. ADK constructs augmented prompt                           │
│     "User asked: What is A2A Protocol?                       │
│      Retrieved context: [chunks from step 4]                 │
│      Please answer based on the context above."              │
│     ↓                                                          │
│  6. Calls Gemini LLM with augmented prompt                   │
│     ↓                                                          │
│  7. LLM generates grounded response                          │
│     "A2A Protocol is Agent-to-Agent communication that..."   │
│     ↓                                                          │
│  8. FastAPI returns response to browser                      │
│     { "response": "A2A Protocol is..." }                     │
│     ↓                                                          │
│  9. Browser displays in chat UI                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Code Structure

**File**: [`agents/orchestrator_agent/agent.py`](../agents/orchestrator_agent/agent.py)
- Defines ADK `Agent` with `RemoteA2aAgent` pointing to Retriever
- Key: `RemoteA2aAgent(url=RETRIEVER_AGENT_URL + "/.well-known/agent-card.json")`

**File**: [`agents/orchestrator_agent/main.py`](../agents/orchestrator_agent/main.py)
- FastAPI app serving web UI and API endpoints
- Uses `get_fast_api_app()` from Google ADK
- Routes: `/message` (POST), `/` (GET), etc.

### Key Implementation Details

**RemoteA2aAgent Definition:**
```python
from google.adk import Agent, RemoteA2aAgent

orchestrator = Agent(
    instructions="You are a helpful assistant...",
    tools=[
        RemoteA2aAgent(
            url=f"{RETRIEVER_AGENT_URL}/.well-known/agent-card.json",
            name="retriever"
        )
    ]
)
```

**What RemoteA2aAgent Does:**
1. Fetches agent card from Retriever's `.well-known/agent-card.json`
2. Adds Retriever's tools to Orchestrator's available toolset
3. When LLM calls a Retriever tool, sends JSON-RPC call over HTTP
4. Returns result to LLM for final synthesis

### Debugging/Verification Commands

```powershell
# 1. Check if orchestrator is running
curl http://localhost:8002/

# 2. Get web UI
start http://localhost:8002

# 3. Verify it can reach retriever
curl http://localhost:8081/.well-known/agent-card.json

# 4. Check environment variables
$env:RETRIEVER_AGENT_URL
# Expected: http://localhost:8081

# 5. View FastAPI logs
# (Check terminal where orchestrator is running)

# 6. Test end-to-end query
$body = @{ message = "What is RAG Engine?" } | ConvertTo-Json
curl -Method POST `
  -Uri http://localhost:8002/message `
  -ContentType "application/json" `
  -Body $body
```

---

## Component 3: Ingestion Service (Document Processing)

**Purpose**: Automatically keeps your RAG corpus up-to-date with new documents from Cloud Storage. Runs on a schedule (daily by default).

**Technical Details:**

```
┌────────────────────────────────────────────────────────────────┐
│  Ingestion Pipeline (Step-by-Step)                             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Triggered by: Cloud Scheduler (daily cron job)               │
│                                                                │
│  Step 1: Cloud Scheduler sends HTTPS request                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ POST https://ingestion-service-xxx.run.app/              │ │
│  │ Authorization: Bearer <OIDC token>                       │ │
│  │ (Proof scheduler's identity, no API key needed)          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ↓                                     │
│  Step 2: Ingestion service starts                            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 1. Get or create RAG corpus                              │ │
│  │    corpus_id = rag.get_corpus() or rag.create_corpus()   │ │
│  │ 2. List all files in GCS bucket                          │ │
│  │    files = gsutil ls gs://bucket/*                       │ │
│  │ 3. Import each file into corpus                          │ │
│  │    rag.import_files(corpus_id, "gs://bucket/*")          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ↓                                     │
│  Step 3: RAG Engine processes documents                       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ For each document:                                       │ │
│  │ 1. Split into chunks (512 tokens, 100-token overlap)    │ │
│  │ 2. Convert each chunk to embedding (text-emb-005)        │ │
│  │ 3. Index in Spanner (Google's vector database)           │ │
│  │                                                           │ │
│  │ Result: Corpus ready for semantic search                 │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ↓                                     │
│  Step 4: Service responds                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 200 OK                                                   │ │
│  │ {                                                        │ │
│  │   "status": "success",                                   │ │
│  │   "corpus_id": "4611686018427387904",                    │ │
│  │   "documents_imported": 4,                               │ │
│  │   "total_chunks": 182                                    │ │
│  │ }                                                        │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ↓                                     │
│  ✅ Knowledge base is fresh and ready for queries             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Code Structure

**File**: [`ingestion/ingest.py`](../ingestion/ingest.py)
- Pure Python script using `vertexai.preview.rag` SDK
- Creates corpus and imports documents

**File**: [`ingestion/app.py`](../ingestion/app.py) (if exists)
- Flask wrapper for Cloud Scheduler integration
- Endpoint: `POST /` to trigger ingestion

### Key Implementation Details

**Document Chunking Strategy:**
```python
from vertexai.preview.rag import rag

# Chunking parameters (in ingestion/ingest.py)
chunk_size = 512        # tokens per chunk
overlap = 100           # tokens overlapping between chunks

# Why overlap?
# Chunks without overlap can split concepts at boundaries
# Example: "RAG Engine is [CHUNK 1 END] ... [CHUNK 2 START] retrieval"
# Overlap ensures semantic continuity across chunks

# Calculate: If document is 2000 tokens
# Chunks (512 each, 100 overlap):
# Chunk 1: tokens 0-512
# Chunk 2: tokens 412-924    (412-512 overlap with chunk 1)
# Chunk 3: tokens 824-1336   (824-924 overlap with chunk 2)
# ... repeat until document end
```

**Embedding Model:**
```
text-embedding-005 (Vertex AI native)
• 768-dimensional vectors
• Optimized for semantic search
• Trained on wide range of domains
• Very fast (~50k tokens/second)

Why embeddings?
Query: "What is machine learning?"
Document chunks have embeddings too
RAG Engine computes: similarity(query_embedding, chunk_embedding)
Returns chunks with highest similarity scores
```

**Idempotent Design:**
```python
# ✅ Safe to run multiple times:
# - get_corpus() returns existing corpus (doesn't create duplicate)
# - import_files() re-indexes existing documents (updates vectors)
# - No side effects if run twice in one day
```

### Debugging/Verification Commands

```powershell
# 1. Run ingestion manually (for testing)
cd ingestion
python ingest.py

# 2. List documents in corpus
gcloud ai documents list-files `
  --rag-corpus=4611686018427387904 `
  --location=europe-west4

# 3. Check Cloud Scheduler job
gcloud scheduler jobs list --location=europe-west4

# 4. View scheduler job details
gcloud scheduler jobs describe ingest-corpus-job `
  --location=europe-west4 `
  --format=json

# 5. See Cloud Scheduler execution history
gcloud scheduler jobs describe ingest-corpus-job `
  --location=europe-west4 `
  --format="value(state)"

# 6. Manually trigger scheduler job (for testing)
gcloud scheduler jobs run ingest-corpus-job `
  --location=europe-west4

# 7. Check Cloud Logging for ingestion job
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ingestion" `
  --limit 50 --format json
```

---

## Component 4: Cloud Storage (Data Repository)

**Purpose**: Stores source documents that RAG Engine will index and retrieve from.

### Architecture

```
GCS Bucket: gs://agenticaigcplearn-adk-docs/
├── a2a_protocol_overview.md          (sample doc)
├── adk_overview.md                   (sample doc)
├── rag_engine_overview.md            (sample doc)
└── vertex_ai_overview.md             (sample doc)

→ Ingestion Service reads all files
→ RAG Engine chunks, embeds, and indexes
→ Retriever searches for semantic matches
```

### Debugging/Verification Commands

```powershell
# 1. List bucket contents
gsutil ls gs://agenticaigcplearn-adk-docs/

# 2. Count files
gsutil ls gs://agenticaigcplearn-adk-docs/ | Measure-Object -Line

# 3. View file size
gsutil ls -h gs://agenticaigcplearn-adk-docs/

# 4. Read a file
gsutil cat gs://agenticaigcplearn-adk-docs/rag_engine_overview.md | head -50

# 5. Upload a new document (for testing)
gsutil cp my_document.md gs://agenticaigcplearn-adk-docs/

# 6. Delete a document (careful!)
gsutil rm gs://agenticaigcplearn-adk-docs/old_doc.md

# 7. Check bucket versioning (for recovery)
gsutil versioning get gs://agenticaigcplearn-adk-docs/

# 8. Check bucket retention (for cost management)
gsutil lifecycle get gs://agenticaigcplearn-adk-docs/
```

---

## Technical Flow: Query-to-Answer Pipeline

**End-to-end request flow with timing:**

```
User types: "What is A2A Protocol?"
│
├─ [T+0ms] Browser sends HTTP POST to Orchestrator
│  POST http://localhost:8002/message
│  Body: { "message": "What is A2A Protocol?" }
│
├─ [T+50ms] Orchestrator receives, passes to ADK Agent
│
├─ [T+100ms] ADK prompts Gemini LLM:
│  "You have access to: retrieve(query)
│   User question: What is A2A Protocol?
│   What tools do you need?"
│
├─ [T+300ms] Gemini responds: "I'll use retrieve to search KB"
│
├─ [T+320ms] Orchestrator calls RemoteA2aAgent.retrieve("A2A Protocol")
│
├─ [T+330ms] RemoteA2aAgent makes HTTP POST to Retriever:
│  POST http://localhost:8081/
│  { "jsonrpc": "2.0", "method": "retrieve", ... }
│
├─ [T+350ms] Retriever receives, converts query to embedding
│
├─ [T+400ms] Retriever calls Vertex AI RAG Engine:
│  Query: embedding of "A2A Protocol"
│  Corpus: 4611686018427387904
│
├─ [T+600ms] RAG Engine returns top 10 chunks:
│  • a2a_protocol_overview.md: "A2A is Agent-to-Agent..."
│  • adk_overview.md: "Agents communicate via A2A..."
│  • ...
│
├─ [T+610ms] Retriever returns chunks to Orchestrator
│
├─ [T+620ms] Orchestrator prompts Gemini again:
│  "User question: What is A2A Protocol?
│   Retrieved context: [chunks from above]
│   Please provide a grounded answer."
│
├─ [T+850ms] Gemini generates response:
│  "A2A (Agent-to-Agent) Protocol is a communication standard
│   used by Google's ADK agents. It enables agents to..."
│
├─ [T+860ms] Orchestrator returns response to browser
│
└─ [T+900ms] Browser displays answer to user

Total latency: ~900ms for full round-trip
Breakdowndown:
  • Network/serialization: ~200ms
  • LLM inference: ~500ms
  • RAG retrieval: ~200ms
  • Processing overhead: ~0ms
```

---

## Design Decisions & Trade-offs

### Why Separate Retriever Agent?

| Benefit | Reason |
|---|---|
| **Single Responsibility** | Retriever only retrieves; Orchestrator only orchestrates |
| **Scalability** | Can scale retriever independently (more search load) |
| **Reusability** | Other agents can use same retriever via A2A |
| **Testing** | Can test retriever in isolation |
| **Deployment** | Can deploy/update independently |

### Why A2A Protocol?

| Benefit | Alternative | Why Better |
|---|---|---|
| **Discoverable** | Agent card auto-describes capabilities | Custom REST would need docs |
| **Standardized** | JSON-RPC 2.0 over HTTP | Custom protocol harder to maintain |
| **Type-Safe** | Schema-driven tool invocation | Manual validation error-prone |
| **Google-Native** | Built into Google ADK | External libraries add complexity |

### Why RAG Engine vs. Hand-Built Vector DB?

| Feature | RAG Engine | Hand-built Pinecone/Weaviate |
|---|---|---|
| **Setup Time** | 5 mins | 2+ hours |
| **Chunking** | Automatic | Manual tuning needed |
| **Embeddings** | Built-in (latest models) | Must manage separately |
| **Scaling** | Google-managed | You manage |
| **Cost** | Pay-per-use | Fixed subscription |
| **Integration** | Native Vertex AI | Extra SDK needed |

---

## Architecture in Different Deployment Modes

### Local Development (Your Laptop)

```
Browser (localhost:8002)
    ↓ HTTP
Orchestrator (localhost:8002)
    ↓ A2A/HTTP
Retriever (localhost:8081)
    ↓ Vertex AI API
Google Cloud (Gemini + RAG Engine)
    ↓
Your Documents (indexed in Corpus)
```

### Production (Cloud Run)

```
Browser (https://orchestrator-xxx.run.app)
    ↓ HTTPS
Cloud Run: Orchestrator Service
    ↓ A2A/HTTPS (internal Google network)
Cloud Run: Retriever Service
    ↓ Vertex AI API
Google Cloud (Gemini + RAG Engine)
    ↓
Your Documents (indexed in Corpus)
```

### Differences

| Aspect | Local | Production |
|---|---|---|
| **Protocol** | HTTP (no encryption) | HTTPS (encrypted) |
| **Hostnames** | `localhost` | `*.run.app` FQDN |
| **Ports** | Explicit (8081, 8002) | Port 443 (no port in URL) |
| **Scaling** | Single machine | Auto-scales per service |
| **Uptime** | While laptop on | 99.95% SLA |
| **Cost** | Zero | ~$0.05/month if low traffic |

---

## Why RAG Engine Instead of Hand-Rolled Vector Database?

**Vertex AI RAG Engine** manages the complete pipeline:

```
Document Upload
    ↓
[RAG Engine: Chunking (512 tokens, 100 overlap)]
    ↓
[RAG Engine: Embedding (text-embedding-005)]
    ↓
[RAG Engine: Indexing (Spanner vector DB)]
    ↓
[RAG Engine: Search (semantic similarity)]
    ↓
Relevant Chunks → Orchestrator → LLM → Grounded Answer
```

**Hand-rolled alternative** (more work, same result):

```
Document Upload
    ↓
[Your code: Chunking (you choose parameters)]
    ↓
[Your code: Call Vertex Embeddings API]
    ↓
[Your code: Setup + manage Pinecone/Weaviate]
    ↓
[Your code: Store embeddings]
    ↓
[Your code: Query, filter, rank results]
    ↓
Relevant Chunks → Orchestrator → LLM → Grounded Answer
```

**Trade-off**:
- ✅ RAG Engine: Less code, automatic optimization, native integration
- ❌ RAG Engine: Less control over chunking/embedding strategies
- ✅ Hand-rolled: Full control, reusable for other projects
- ❌ Hand-rolled: More infrastructure, more maintenance

---

## Security Architecture

**Current State (Development):**
```
❌ Unauthenticated Cloud Run services
  • Anyone with URL can call endpoints
  • Okay for learning in personal project
  • NOT okay for production
```

**Recommended Production State:**
```
┌──────────────────────────────────────────┐
│  User (Authenticated)                    │
│  • Login: email + password               │
│  • Session: JWT token                    │
└──────────────────────────────────────────┘
         ↓ HTTPS + Bearer token
┌──────────────────────────────────────────┐
│  Cloud IAM / Identity Platform           │
│  • Verify JWT signature                  │
│  • Check authorization (roles/perms)     │
└──────────────────────────────────────────┘
         ↓ HTTPS + OIDC token
┌──────────────────────────────────────────┐
│  Cloud Run: Orchestrator (private)       │
│  • Requires roles/run.invoker             │
│  • Uses Workload Identity                │
└──────────────────────────────────────────┘
         ↓ A2A/HTTPS + OIDC token
┌──────────────────────────────────────────┐
│  Cloud Run: Retriever (private)          │
│  • Requires roles/run.invoker             │
│  • Uses Workload Identity                │
└──────────────────────────────────────────┘
         ↓ Vertex AI API
┌──────────────────────────────────────────┐
│  Vertex AI (Google-managed)              │
│  • Automatic encryption at rest          │
│  • Audit logging                         │
└──────────────────────────────────────────┘
```

**Hardening Checklist:**
- ☐ Redeploy with `--no-allow-unauthenticated`
- ☐ Set up Cloud Identity Platform or Auth0
- ☐ Grant `roles/run.invoker` only to authenticated users
- ☐ Configure Retriever with `auth_scheme="oidc"` for A2A
- ☐ Enable Cloud Audit Logging for all services
- ☐ Set up Cloud Armor for DDoS protection
- ☐ Use Workload Identity Federation (GitHub Actions don't need keys)

**Never commit to GitHub:**
- `.env` files (contains secrets)
- `service-account-keys.json`
- API keys, tokens, passwords
- Private configuration

---

## Monitoring & Observability

### Cloud Logging

```powershell
# View orchestrator logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=orchestrator-agent" `
  --limit 50 --format json

# View retriever logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=retriever-agent" `
  --limit 50 --format json

# View ingestion logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ingestion" `
  --limit 50 --format json
```

### Metrics to Monitor

| Metric | Tool | Alert Threshold |
|---|---|---|
| Service latency | Cloud Monitoring | > 1000ms |
| Error rate | Cloud Logging | > 1% |
| RAG corpus staleness | Cloud Scheduler logs | > 24h since last run |
| LLM token usage | Vertex AI billing | Budget overage |
| A2A call failures | Cloud Logging | > 5 per minute |

### Common Issues & Diagnostics

| Symptom | Likely Cause | Check |
|---|---|---|
| "Agent card not found" | Retriever not running or URL wrong | `curl <RETRIEVER_URL>/.well-known/agent-card.json` |
| "Origin mismatch" | A2A host/port inconsistency | Retriever HOST vs Orchestrator RETRIEVER_AGENT_URL |
| "Corpus not found" | Wrong corpus ID or location | `gcloud ai documents corpus list` |
| "Slow responses" | LLM or RAG Engine overloaded | Check Vertex AI quotas |
| "Ingestion failed" | Bucket permission or GCS issue | Run ingestion locally with verbose logging |

---

## References

- [Google ADK Documentation](https://ai.google.dev/docs/agents)
- [Vertex AI RAG Engine](https://cloud.google.com/vertex-ai/docs/generative-ai/rag-overview)
- [A2A Protocol Spec](https://ai.google.dev/docs/agents/a2a)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
