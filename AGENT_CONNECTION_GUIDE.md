# Azure Agent Connection Architecture

This document explains **step-by-step** how each agent connects to Azure services.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER REQUEST                                  │
│              (via HTTP/REST endpoint)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│        ORCHESTRATOR AGENT (gpt-4o-mini)                         │
│  ✓ Azure OpenAI (Cognitive Services)                            │
│  ✓ Reads environment variables                                  │
│  ✓ Routes query to SQL Agent or Retriever Agent                │
└─────────┬───────────────────────────────┬──────────────────────┘
          │                               │
          ▼                               ▼
    ┌──────────────────┐         ┌──────────────────────┐
    │  SQL AGENT       │         │ RETRIEVER AGENT      │
    │ (gpt-4o-mini)    │         │  (gpt-4o-mini)       │
    └────────┬─────────┘         └──────┬───────────────┘
             │                          │
             ▼                          ▼
    ┌──────────────────┐         ┌──────────────────────┐
    │ AZURE SQL DB     │         │ AZURE AI SEARCH      │
    │ (Geography Index)│         │ (Knowledge Index)    │
    │                  │         │                      │
    │ • Countries      │         │ • Document chunks    │
    │ • States (28)    │         │ • Embeddings         │
    │ • Districts      │         │ • Semantic search    │
    └──────────────────┘         └──────────────────────┘
```

---

## 1. ORCHESTRATOR AGENT - Central Router

### Purpose
Routes incoming queries to appropriate specialist agents.

### Azure Services Used
- **Azure OpenAI (Cognitive Services)** - LLM inference

### Connection Code

```python
# agents/orchestrator_agent/agent.py

import os
from agent_framework import Agent

# CONNECTION: Read Azure OpenAI details from environment
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

root_agent = Agent(
    model=AZURE_OPENAI_DEPLOYMENT,  # ← Uses deployment name from workflow
    name="orchestrator_agent",
    description="Front-door assistant that routes requests to specialist agents.",
    instruction="""
    ROUTING RULES:
    1. GREETINGS → Respond directly
    2. LIST/META QUERIES → Delegate to sql_agent
    3. DETAILED QUERIES → Delegate to retriever_agent
    """
)
```

### Environment Variables Required

```yaml
AZURE_OPENAI_ENDPOINT:      https://ai-agents-openai.openai.azure.com/
AZURE_OPENAI_API_KEY:       [secret - from Key Vault]
AZURE_OPENAI_DEPLOYMENT:    gpt-4o-mini
```

### Flow Example

**User asks:** "Tell me about Maharashtra"

```
1. Query arrives at Orchestrator
2. Agent reads instruction → Detects "Tell me about" = DETAILED QUERY
3. Routes to retriever_agent
4. Retriever searches Azure AI Search for "Maharashtra culture traditions..."
5. Returns comprehensive answer
```

---

## 2. SQL AGENT - Metadata/Index Queries

### Purpose
Queries Azure SQL Database for geography entity IDs and names.

### Azure Services Used
- **Azure OpenAI (Cognitive Services)** - LLM inference
- **Azure SQL Database** - Geography index queries

### Connection Code

```python
# agents/sql_agent/agent.py

import os
import pyodbc
from agent_framework import Agent

# CONNECTION 1: Azure SQL Database
_sql_server = os.environ.get("AZURE_SQL_SERVER")           # e.g., "ai-agents-sql.database.windows.net"
_sql_database = os.environ.get("AZURE_SQL_DATABASE", "geography_index")
_sql_user = os.environ.get("AZURE_SQL_USERNAME")            # sqladmin
_sql_password = os.environ.get("AZURE_SQL_PASSWORD")        # [secret]

# Build connection string
_connection_string = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server=tcp:{_sql_server},1433;"                        # ← TCP port
    f"Database={_sql_database};"
    f"Uid={_sql_user};"
    f"Pwd={_sql_password};"
    f"Encrypt=yes;"                                          # ← TLS encryption
    f"TrustServerCertificate=no;"
    f"Connection Timeout=30;"
)

# CONNECTION 2: Azure OpenAI for reasoning
root_agent = Agent(
    model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    name="sql_agent",
    description="Database specialist that queries Azure SQL for geography index",
)

# Function to query database
def get_state_info(state_name: str) -> str:
    """Get state index from Azure SQL Database."""
    try:
        # Open connection to Azure SQL
        with pyodbc.connect(_connection_string) as conn:
            cursor = conn.cursor()
            
            # Execute SQL query
            cursor.execute("""
                SELECT s.id, s.name, s.capital, c.name as country_name
                FROM states s
                JOIN countries c ON s.country_id = c.id
                WHERE LOWER(s.name) = LOWER(?) 
                   OR LOWER(s.name) LIKE LOWER(?)
            """, (state_name, f"%{state_name}%"))
            
            row = cursor.fetchone()
            
            if row:
                return f"State: {row.name} (ID: {row.id}, Capital: {row.capital})"
            return f"State '{state_name}' not found"
    
    except Exception as e:
        return f"Database error: {str(e)}"
```

### Database Schema (Azure SQL)

```sql
-- Table: countries
CREATE TABLE countries (
    id INT PRIMARY KEY,
    name NVARCHAR(100),
    capital NVARCHAR(100)
)

-- Table: states  
CREATE TABLE states (
    id INT PRIMARY KEY,
    name NVARCHAR(100),
    capital NVARCHAR(100),
    country_id INT,
    FOREIGN KEY (country_id) REFERENCES countries(id)
)

-- Example data (populated by infra/setup_azure_sql.py)
INSERT INTO countries VALUES (1, 'India', 'New Delhi')
INSERT INTO states VALUES (1, 'Andhra Pradesh', 'Amaravati', 1)
INSERT INTO states VALUES (2, 'Arunachal Pradesh', 'Itanagar', 1)
INSERT INTO states VALUES (14, 'Maharashtra', 'Mumbai', 1)
... (28 states total)
```

### Environment Variables Required

```yaml
AZURE_SQL_SERVER:           ai-agents-sql.database.windows.net
AZURE_SQL_DATABASE:         geography_index
AZURE_SQL_USERNAME:         sqladmin
AZURE_SQL_PASSWORD:         [secret from Key Vault]
AZURE_OPENAI_ENDPOINT:      https://ai-agents-openai.openai.azure.com/
AZURE_OPENAI_API_KEY:       [secret]
AZURE_OPENAI_DEPLOYMENT:    gpt-4o-mini
```

### Flow Example

**User asks:** "List all states"

```
1. Query reaches Orchestrator → Detects "list all states" = META QUERY
2. Routes to sql_agent (via A2A protocol)
3. sql_agent.list_all_states() executes:
   - Connects to Azure SQL using pyodbc
   - SELECT * FROM states ORDER BY name
   - Returns 28 rows with capitals
4. Returns formatted list to user
```

---

## 3. RETRIEVER AGENT - RAG Search

### Purpose
Searches Azure AI Search index for detailed information using semantic (vector) search.

### Azure Services Used
- **Azure OpenAI (Cognitive Services)** - LLM inference + embeddings
- **Azure AI Search** - Vector/semantic search over documents

### Connection Code

```python
# agents/retriever_agent/agent.py

import os
from agent_framework import Agent
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# CONNECTION 1: Azure AI Search
_search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")     # https://ai-agents-search.search.windows.net
_search_key = os.environ.get("AZURE_SEARCH_KEY")               # [admin key]
_search_index = os.environ.get("AZURE_SEARCH_INDEX", "documents")

search_client = SearchClient(
    endpoint=_search_endpoint,
    index_name=_search_index,
    credential=AzureKeyCredential(_search_key)
)

# CONNECTION 2: Azure OpenAI for reasoning
root_agent = Agent(
    model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    name="retriever_agent",
    description="Specialist agent that answers questions using Azure AI Search RAG",
)

def search_knowledge_base(query: str, top_k: int = 10) -> str:
    """
    Search Azure AI Search index for relevant passages.
    
    Connection flow:
    1. Client sends query: "Maharashtra culture traditions"
    2. Azure AI Search converts query to embeddings (1536 dimensions)
    3. Uses HNSW algorithm to find k nearest neighbors
    4. Returns top 10 documents sorted by relevance
    """
    try:
        results = search_client.search(
            search_text=query,                    # ← Natural language query
            top=top_k,                           # ← Return top 10 results
            select=["content", "title", "chunk_id"],  # ← Fields to retrieve
            query_type="semantic",               # ← Semantic (vector) search
            semantic_configuration_name="default"
        )
        
        passages = []
        for result in results:
            content = result.get("content", "")
            title = result.get("title", "")
            passages.append(f"[{title}]\n{content}")
        
        if passages:
            return "\n\n---\n\n".join(passages)
        return "No relevant information found"
    
    except Exception as e:
        return f"Search error: {str(e)}"
```

### Azure AI Search Index Schema

```json
{
  "name": "documents",
  "fields": [
    {
      "name": "id",
      "type": "Edm.String",
      "key": true,
      "retrievable": true
    },
    {
      "name": "content",
      "type": "Edm.String",
      "searchable": true,
      "retrievable": true,
      "analyzer": "standard.lucene"
    },
    {
      "name": "title",
      "type": "Edm.String",
      "retrievable": true
    },
    {
      "name": "embedding",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "retrievable": true,
      "dimensions": 1536,
      "vectorSearchConfiguration": "myHnsw"
    },
    {
      "name": "chunk_id",
      "type": "Edm.String",
      "retrievable": true
    }
  ],
  "vectorSearch": {
    "algorithms": [
      {
        "name": "myHnsw",
        "kind": "hnsw"
      }
    ]
  }
}
```

### Environment Variables Required

```yaml
AZURE_SEARCH_ENDPOINT:      https://ai-agents-search.search.windows.net
AZURE_SEARCH_KEY:           [admin key from Key Vault]
AZURE_SEARCH_INDEX:         documents
AZURE_OPENAI_ENDPOINT:      https://ai-agents-openai.openai.azure.com/
AZURE_OPENAI_API_KEY:       [secret]
AZURE_OPENAI_DEPLOYMENT:    gpt-4o-mini
```

### Flow Example

**User asks:** "Tell me about Maharashtra culture"

```
1. Query reaches Orchestrator → Routes to retriever_agent
2. retriever_agent.search_knowledge_base() executes:
   
   Step 1: Query Vectorization
   - Query: "Maharashtra culture traditions festivals arts"
   - Azure OpenAI creates embedding vector (1536 dimensions)
   
   Step 2: Semantic Search
   - Sends query vector to Azure AI Search
   - HNSW algorithm finds 10 nearest document chunks
   - Scoring: semantic similarity (0-1)
   
   Step 3: Results Retrieval
   - Returns top 10 passages from states.md
   - Each contains: [title], content, chunk_id
   
   Step 4: Synthesis
   - Agent reads passages
   - LLM synthesizes comprehensive answer
   - Cites source documents
```

---

## 4. DOCUMENT INGESTION - Loading Data

### Purpose
Loads markdown documents into Azure AI Search index.

### Azure Services Used
- **Azure Blob Storage** - Document storage
- **Azure AI Search** - Index creation & embedding generation
- **Azure OpenAI** - Embedding model for vectors

### Ingestion Process

```python
# ingestion/ingest.py (simplified for Azure)

import os
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

# CONNECTION: Azure AI Search
search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
search_key = os.environ.get("AZURE_SEARCH_KEY")
search_index = os.environ.get("AZURE_SEARCH_INDEX", "documents")

index_client = SearchIndexClient(endpoint=search_endpoint, credential=AzureKeyCredential(search_key))
search_client = SearchClient(endpoint=search_endpoint, index_name=search_index, credential=AzureKeyCredential(search_key))

def ingest_documents(documents_path: str):
    """
    Load markdown documents into Azure AI Search.
    
    Flow:
    1. Read files from data/sample_docs/
    2. Chunk documents into 512-token chunks
    3. Generate embeddings via Azure OpenAI
    4. Upload to Azure AI Search index
    """
    
    # Sample documents (stored locally)
    docs = [
        {"title": "states.md", "path": "data/sample_docs/states.md"},
        {"title": "india.md", "path": "data/sample_docs/india.md"},
        {"title": "districtandplace.md", "path": "data/sample_docs/districtandplace.md"},
    ]
    
    documents_to_upload = []
    
    for doc_info in docs:
        with open(doc_info["path"], "r", encoding="utf-8") as f:
            content = f.read()
            
            # Chunk document (512 tokens, 100 overlap)
            chunks = chunk_text(content, chunk_size=512, overlap=100)
            
            for i, chunk in enumerate(chunks):
                # Generate embedding via Azure OpenAI
                # (using text-embedding-3-large or similar)
                embedding = generate_embedding(chunk)
                
                documents_to_upload.append({
                    "id": f"{doc_info['title']}-chunk-{i}",
                    "title": doc_info["title"],
                    "content": chunk,
                    "embedding": embedding,
                    "chunk_id": i
                })
    
    # Upload batch to Azure AI Search
    result = search_client.upload_documents(documents_to_upload)
    print(f"Uploaded {len(result)} documents to Azure AI Search")
```

### Document Structure (Example)

```markdown
# File: data/sample_docs/states.md

## Maharashtra
Maharashtra is a state located in the southwestern part of India.
Capital: Mumbai

### Culture
- Marathi language
- Classical music (Hindustani)
- Theatre and cinema
- Traditional festivals: Ganesh Chaturthi, Diwali
- Food: Misal Pav, Vada Pav, Puran Poli

### Economy
- IT hub (Pune, Mumbai)
- Film industry (Bollywood)
- Automotive sector
- Textiles and agriculture
- Manufacturing: 40% of India's auto industry

---

## Andhra Pradesh
Capital: Amaravati
...
```

### Environment Variables Required

```yaml
AZURE_SEARCH_ENDPOINT:      https://ai-agents-search.search.windows.net
AZURE_SEARCH_KEY:           [admin key]
AZURE_SEARCH_INDEX:         documents
AZURE_OPENAI_ENDPOINT:      https://ai-agents-openai.openai.azure.com/
AZURE_OPENAI_API_KEY:       [secret]
```

### Ingestion Trigger (GitHub Actions)

```yaml
# .github/workflows/deploy.yml

- name: Upload Documents to AI Search
  run: |
    python ingestion/ingest.py
```

---

## Complete End-to-End Flow

### Scenario: User Query "What is the culture of Kerala?"

```
STEP 1: User sends query
┌──────────────────────────────────────────────────────┐
│ User: "What is the culture of Kerala?"               │
│ Via: HTTP POST to /chat endpoint                     │
└──────────────┬───────────────────────────────────────┘
               │
STEP 2: Orchestrator receives query
├─ Reads from Azure OpenAI deployment (gpt-4o-mini)
├─ Instruction says: "culture of X" → route to retriever_agent
└────────────────┬────────────────────────────────────
                 │
STEP 3: Retriever Agent processes
├─ Calls search_knowledge_base("Kerala culture traditions festivals")
├─ SearchClient connects to Azure AI Search
├─ Query embedded via Azure OpenAI (text-embedding-3-large)
├─ HNSW search returns 10 chunks from states.md
└────────────────┬────────────────────────────────────
                 │
STEP 4: Azure AI Search performs semantic search
├─ Matches: "Kerala" sections from indexed documents
├─ Returns chunks about:
│  - Kathakali dance
│  - Ayurveda tradition
│  - Backwaters culture
│  - Spice trade heritage
│  - Kerala cuisine
│  - Christian, Hindu, Muslim traditions
└────────────────┬────────────────────────────────────
                 │
STEP 5: Retriever synthesizes answer
├─ Reads all 10 passages
├─ Uses GPT-4o Mini to synthesize comprehensive answer
├─ Cites source: "states.md"
└────────────────┬────────────────────────────────────
                 │
STEP 6: Return to user
└─ Comprehensive answer about Kerala's rich cultural heritage

USER RESPONSE:
┌──────────────────────────────────────────────────────┐
│ Kerala has a vibrant and unique culture shaped by    │
│ its diverse communities and maritime heritage:       │
│                                                       │
│ PERFORMING ARTS:                                     │
│ - Kathakali classical dance                          │
│ - Koodiyatta shadow puppet theatre                   │
│ - Mohiniyattam dance form                           │
│                                                       │
│ TRADITIONS:                                          │
│ - Ayurveda ancient medicine system                   │
│ - Backwater houseboat traditions                     │
│ - Spice trade heritage                              │
│ - Matrilineal Nair community traditions              │
│                                                       │
│ CUISINE:                                             │
│ - Coconut-based curries                             │
│ - Appam, puttu, idiyappam                           │
│ - Fresh seafood                                      │
│                                                       │
│ RELIGIONS:                                           │
│ - Hinduism (41%)                                    │
│ - Christianity (19%)                                │
│ - Islam (25%)                                       │
│                                                       │
│ [Source: states.md]                                 │
└──────────────────────────────────────────────────────┘
```

---

## Environment Variables Summary

### Required for ALL Agents
```yaml
# Azure OpenAI (Cognitive Services)
AZURE_OPENAI_ENDPOINT:      https://ai-agents-openai.openai.azure.com/
AZURE_OPENAI_API_KEY:       [secret from Key Vault]
AZURE_OPENAI_DEPLOYMENT:    gpt-4o-mini
```

### Required for SQL Agent
```yaml
# Azure SQL Database
AZURE_SQL_SERVER:           ai-agents-sql.database.windows.net
AZURE_SQL_DATABASE:         geography_index
AZURE_SQL_USERNAME:         sqladmin
AZURE_SQL_PASSWORD:         [secret from Key Vault]
```

### Required for Retriever Agent
```yaml
# Azure AI Search
AZURE_SEARCH_ENDPOINT:      https://ai-agents-search.search.windows.net
AZURE_SEARCH_KEY:           [admin key from Key Vault]
AZURE_SEARCH_INDEX:         documents
```

### Optional
```yaml
RETRIEVER_URL:              http://localhost:8081  # For local testing
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER APPLICATION                               │
│                       (Web/Chat Interface)                              │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                    HTTP Request: POST /chat
                                 │
                ┌────────────────▼───────────────┐
                │  ORCHESTRATOR AGENT SERVICE    │
                │  (Container App / FastAPI)     │
                │                                 │
                │  ✓ Reads query                  │
                │  ✓ Routes to specialist agents  │
                │                                 │
                │  Connections:                   │
                │  └─ Azure OpenAI (gpt-4o-mini)  │
                └────────┬──────────────┬─────────┘
                         │              │
         A2A Protocol    │              │  A2A Protocol
                         │              │
         ┌───────────────▼──┐    ┌──────▼──────────────┐
         │   SQL AGENT      │    │  RETRIEVER AGENT   │
         │   (Container App)│    │  (Container App)   │
         │                  │    │                    │
         │ Connections:     │    │  Connections:      │
         │ ├─ OpenAI        │    │  ├─ OpenAI         │
         │ └─ SQL Database  │    │  └─ AI Search      │
         └────────┬─────────┘    └──────┬─────────────┘
                  │                     │
                  │                     │
        ┌─────────▼──────────┐   ┌──────▼──────────┐
        │  AZURE SQL DB      │   │  AZURE AI       │
        │  geography_index   │   │  SEARCH         │
        │                    │   │  Index:         │
        │  Tables:           │   │  "documents"    │
        │  • countries       │   │                 │
        │  • states (28)     │   │  Chunked docs:  │
        │  • districts       │   │  • states.md    │
        │                    │   │  • india.md     │
        │  Connections:      │   │  • districts.md │
        │  ├─ pyodbc         │   │                 │
        │  ├─ TLS encrypted  │   │  Connections:   │
        │  └─ TCP:1433       │   │  ├─ REST API    │
        │                    │   │  ├─ Embeddings  │
        │                    │   │  └─ Semantic    │
        │                    │   │     search      │
        └────────────────────┘   └─────────────────┘
        
┌────────────────────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE (One-time)                       │
│                                                                          │
│ Load documents: data/sample_docs/*.md                                   │
│        ↓                                                                 │
│ Chunk (512 tokens, 100 overlap)                                         │
│        ↓                                                                 │
│ Generate embeddings (Azure OpenAI text-embedding model)                │
│        ↓                                                                 │
│ Upload to Azure AI Search index                                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### 1. **A2A Protocol (Agent-to-Agent)**
- Microsoft Agent Framework communication standard
- Orchestrator → SQL Agent: via REST/HTTP
- Orchestrator → Retriever Agent: via REST/HTTP
- Structured JSON message passing
- See: `agent_framework.Agent.delegate()`

### 2. **Semantic Search (vs Keyword Search)**
- Query gets converted to 1536-dimensional embedding vector
- Compared against document chunk embeddings
- Uses HNSW algorithm (hierarchical navigable small world)
- Much better than keyword matching for natural language

### 3. **Chunking Strategy**
- Documents split into 512-token chunks
- 100-token overlap between chunks
- Prevents cutting off mid-sentence
- Improves search relevance

### 4. **Deployment Model**
- Container Apps = serverless containers
- 0-10 replicas (autoscaling)
- Environment variables passed via secrets
- Health checks every 30 seconds

---

## Testing Locally

```bash
# Set environment variables
export AZURE_OPENAI_ENDPOINT="https://ai-agents-openai.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
export AZURE_SQL_SERVER="ai-agents-sql.database.windows.net"
export AZURE_SQL_DATABASE="geography_index"
export AZURE_SQL_USERNAME="sqladmin"
export AZURE_SQL_PASSWORD="your-password"
export AZURE_SEARCH_ENDPOINT="https://ai-agents-search.search.windows.net"
export AZURE_SEARCH_KEY="your-key"
export AZURE_SEARCH_INDEX="documents"

# Run locally
cd agents/orchestrator_agent
python -m uvicorn main:app --reload --port 8002
```

---

## Common Connection Issues & Fixes

| Issue | Cause | Solution |
|-------|-------|----------|
| `Connection timeout to SQL` | Firewall rule missing | Add "Allow Azure services" rule in SQL settings |
| `Authentication failed (OpenAI)` | Invalid key or endpoint | Check secrets in Key Vault |
| `No results from search` | Documents not ingested | Run `python ingestion/ingest.py` |
| `ODBC Driver not found` | Missing SQL driver | Install "ODBC Driver 18 for SQL Server" |
| `Embedding mismatch` | Wrong embedding dimensions | Ensure 1536 dimensions in index schema |
| `Agent routing fails` | Instruction not clear | Review routing rules in agent instruction |

---

## Security Best Practices

1. **Never hardcode secrets** - Use Azure Key Vault
2. **Use managed identities** - Container Apps to services (no keys in memory)
3. **TLS encryption** - All connections encrypted
4. **Network isolation** - Virtual Network / Private Endpoints
5. **RBAC** - Role-based access control per service
6. **Audit logging** - Track all data access

---

## Next Steps

- **Monitor performance**: Application Insights for latency/errors
- **Scale retriever**: Increase replicas for high traffic
- **Add authentication**: OAuth 2.0 / Azure AD on endpoints
- **Optimize search**: Tune ranking weights, semantic config
- **Extend knowledge**: Add more documents to ingestion
