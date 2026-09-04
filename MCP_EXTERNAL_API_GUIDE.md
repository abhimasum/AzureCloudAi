# MCP (Model Context Protocol) - External API Connections

This guide explains how to connect agents to external APIs using Model Context Protocol (MCP).

---

## What is MCP?

**MCP** is a standardized protocol that allows agents to:
- Call external services/APIs
- Access tools dynamically
- Share resources across agents
- Maintain secure credential management

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT (LLM)                                │
│              (Orchestrator, SQL, Retriever)                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ MCP Protocol (JSON-RPC)
                     │ TCP/HTTP/Stdio
                     ▼
         ┌─────────────────────────┐
         │   MCP SERVER            │
         │                         │
         │  - Tools (callables)    │
         │  - Resources (data)     │
         │  - Prompts (templates)  │
         └────────┬────────────────┘
                  │
                  │ HTTP/REST
                  │
                  ▼
         ┌─────────────────────────┐
         │  EXTERNAL API           │
         │  (Weather, News, DB,    │
         │   Payment, etc.)        │
         └─────────────────────────┘
```

---

## Architecture: How MCP Connects External APIs

### 1. MCP Server Architecture

```python
# mcp_servers/weather_api_server.py
"""
MCP Server that exposes weather APIs as tools for agents.
"""

import json
from mcp.server import Server
from mcp.types import Tool, TextContent

# Initialize MCP Server
server = Server("weather-api-server")

# Define tools that agents can call
@server.tool()
async def get_weather(location: str, units: str = "metric") -> str:
    """
    Get current weather for a location.
    
    Args:
        location: City name (e.g., "Mumbai")
        units: "metric" (Celsius) or "imperial" (Fahrenheit)
    
    Returns:
        JSON string with temperature, humidity, conditions
    """
    import httpx
    
    # External API call
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": location,
                "units": units,
                "appid": os.environ["OPENWEATHER_API_KEY"]
            }
        )
        return response.json()


@server.tool()
async def get_forecast(location: str, days: int = 5) -> str:
    """
    Get weather forecast for a location.
    
    Args:
        location: City name
        days: Number of days (1-5)
    
    Returns:
        JSON array of daily forecasts
    """
    import httpx
    
    async with httpx.AsyncClient() as client:
        # Call external API
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={
                "q": location,
                "cnt": days * 8,  # 8 forecasts per day
                "appid": os.environ["OPENWEATHER_API_KEY"]
            }
        )
        return response.json()


if __name__ == "__main__":
    # Start MCP server on stdio/TCP
    server.run_stdio()  # or server.run_tcp(host="0.0.0.0", port=5000)
```

### 2. Registering MCP Server with Agents

```python
# agents/orchestrator_agent/agent.py
"""
Orchestrator that can call external APIs via MCP servers.
"""

import os
from agent_framework import Agent
from mcp.client import ClientSession
from mcp.stdio_client import StdioClientTransport

# Initialize MCP client connection to weather API server
weather_mcp = ClientSession(
    transport=StdioClientTransport(
        command=["python", "-m", "mcp_servers.weather_api_server"],
        env={
            "OPENWEATHER_API_KEY": os.environ["OPENWEATHER_API_KEY"]
        }
    )
)

root_agent = Agent(
    model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    name="orchestrator_agent",
    description="Front-door assistant with access to external APIs",
    
    # Connect MCP tools to agent
    tools=[
        weather_mcp.get_tool("get_weather"),
        weather_mcp.get_tool("get_forecast"),
    ],
    
    instruction="""
You are an orchestrator agent with access to weather data.

AVAILABLE TOOLS:
1. get_weather(location, units) → Get current weather
2. get_forecast(location, days) → Get weather forecast

When user asks about weather:
1. Use get_weather() to get current conditions
2. Optionally use get_forecast() for upcoming days
3. Format response with temperature, humidity, conditions
4. Include weather alerts if available

Example:
- User: "What's the weather in Mumbai?"
- You: Call get_weather("Mumbai", "metric")
- Return: "Currently 28°C in Mumbai, scattered clouds, 65% humidity"
    """
)
```

---

## Real-World Example: Weather + Geography Integration

### Scenario: User asks "Tell me about Kerala weather and culture"

```python
# agents/orchestrator_agent/agent.py

import os
from agent_framework import Agent
from mcp.client import ClientSession
from mcp.stdio_client import StdioClientTransport

# CONNECTION 1: MCP Server for Weather API
weather_mcp = ClientSession(
    transport=StdioClientTransport(
        command=["python", "-m", "mcp_servers.weather_api_server"],
        env={"OPENWEATHER_API_KEY": os.environ["OPENWEATHER_API_KEY"]}
    )
)

# CONNECTION 2: MCP Server for News API
news_mcp = ClientSession(
    transport=StdioClientTransport(
        command=["python", "-m", "mcp_servers.news_api_server"],
        env={"NEWSAPI_KEY": os.environ["NEWSAPI_KEY"]}
    )
)

root_agent = Agent(
    model="gpt-4o-mini",
    name="orchestrator",
    
    # Import SQL and Retriever agents (local)
    sub_agents=[sql_agent, retriever_agent],
    
    # Import MCP tools (external APIs)
    tools=[
        weather_mcp.get_tool("get_weather"),
        weather_mcp.get_tool("get_forecast"),
        news_mcp.get_tool("get_state_news"),
    ],
    
    instruction="""
You are an orchestrator with access to:
1. SQL Agent → Database queries
2. Retriever Agent → RAG search
3. Weather API → Current weather & forecast
4. News API → State-specific news

ROUTING LOGIC:
1. "Tell me about [state] culture" → Use retriever_agent (RAG search)
2. "What's the weather in [state]?" → Use get_weather() (MCP)
3. "[State] news?" → Use get_state_news() (MCP)
4. "List all states" → Use sql_agent (database)

COMBINED QUERY EXAMPLE:
User: "Tell me about Kerala weather and culture"
    ↓
You execute:
    1. retriever_agent.search("Kerala culture traditions")
       → Returns: Culture, traditions, festivals
    2. get_weather("Kochi, Kerala", "metric")
       → Returns: 28°C, 75% humidity, scattered clouds
    3. Combine results into comprehensive answer
    """
)
```

---

## MCP Server Types & Configurations

### Type 1: HTTP-based External API (Weather, News, etc.)

```python
# mcp_servers/weather_api_server.py

import os
import json
import httpx
from mcp.server import Server
from mcp.types import Tool

server = Server("weather-api-server")

@server.tool()
async def get_weather(location: str, units: str = "metric") -> dict:
    """Get weather from OpenWeatherMap API"""
    async with httpx.AsyncClient() as client:
        # External API: openweathermap.org
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": location,
                "units": units,
                "appid": os.environ["OPENWEATHER_API_KEY"]
            },
            timeout=10.0
        )
        response.raise_for_status()
        
        data = response.json()
        return {
            "location": location,
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"]
        }

if __name__ == "__main__":
    server.run_stdio()
```

### Type 2: Database API (Query external databases)

```python
# mcp_servers/database_api_server.py

import os
import pyodbc
from mcp.server import Server

server = Server("database-api-server")

# External API: Another Azure SQL database (different from our geography_index)
EXTERNAL_DB_CONNECTION = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server=tcp:{os.environ['EXTERNAL_SQL_SERVER']},1433;"
    f"Database={os.environ['EXTERNAL_SQL_DATABASE']};"
    f"Uid={os.environ['EXTERNAL_SQL_USER']};"
    f"Pwd={os.environ['EXTERNAL_SQL_PASSWORD']};"
    f"Encrypt=yes;TrustServerCertificate=no;"
)

@server.tool()
async def query_tourism_database(state: str) -> dict:
    """Query tourism database for attractions in a state"""
    try:
        with pyodbc.connect(EXTERNAL_DB_CONNECTION) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT attraction_name, description, location, rating
                FROM attractions
                WHERE state = ? AND rating >= 4.0
                ORDER BY rating DESC
                LIMIT 10
            """, (state,))
            
            attractions = []
            for row in cursor.fetchall():
                attractions.append({
                    "name": row[0],
                    "description": row[1],
                    "location": row[2],
                    "rating": row[3]
                })
            
            return {"state": state, "attractions": attractions}
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    server.run_stdio()
```

### Type 3: Payment/Transaction API

```python
# mcp_servers/payment_api_server.py

import os
import stripe
from mcp.server import Server

server = Server("payment-api-server")

# Initialize Stripe (external payment API)
stripe.api_key = os.environ["STRIPE_API_KEY"]

@server.tool()
async def create_payment(amount: float, currency: str = "USD", description: str = "") -> dict:
    """Create a payment via Stripe API"""
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency=currency,
            description=description,
            metadata={"source": "agent"}
        )
        return {
            "payment_id": intent.id,
            "status": intent.status,
            "amount": intent.amount / 100,
            "currency": intent.currency
        }
    except stripe.error.StripeError as e:
        return {"error": str(e)}

if __name__ == "__main__":
    server.run_stdio()
```

---

## Connection Flow: Step-by-Step

### Example: User asks "Weather in Maharashtra + top attractions"

```
STEP 1: User Query Received
┌──────────────────────────────────────────┐
│ "What's the weather in Maharashtra and   │
│ what are top tourist attractions?"        │
└──────────────┬───────────────────────────┘
               │
STEP 2: Agent Routes Query
├─ Detects: weather query + attractions
├─ Loads MCP tools: get_weather()
├─ Loads local agents: retriever_agent
└───────────────┬────────────────────────
                │
STEP 3: Agent Executes Multiple Calls
├─ CALL 1: get_weather("Maharashtra")
│  ├─ MCP client sends JSON-RPC call
│  ├─ Weather MCP server receives
│  ├─ Makes HTTP call: api.openweathermap.org
│  ├─ Returns: 32°C, 65% humidity, partly cloudy
│  └─ Returns to agent
│
├─ CALL 2: retriever_agent.search("Maharashtra attractions")
│  ├─ Calls Azure AI Search
│  ├─ Returns top 10 tourist destinations
│  └─ Returns to agent
│
└─────────────────┬──────────────────────
                  │
STEP 4: Agent Synthesizes Answer
├─ Combines results from weather API + RAG search
├─ Formats response
└───────────────┬──────────────────────
                │
STEP 5: Return to User
┌──────────────────────────────────────────┐
│ Maharashtra Weather:                      │
│ • Temperature: 32°C                       │
│ • Humidity: 65%                          │
│ • Condition: Partly Cloudy               │
│                                           │
│ Top Tourist Attractions:                 │
│ 1. Gateway of India (Mumbai) - Rating: 4.7
│ 2. Ajanta Caves (Aurangabad) - Rating: 4.5
│ 3. Ellora Caves (Aurangabad) - Rating: 4.6
│ 4. Lonar Lake (Buldhana) - Rating: 4.2
│                                           │
│ Best time to visit: October-February     │
└──────────────────────────────────────────┘
```

---

## Deployment: MCP Server in Container Apps

### Docker Container for MCP Server

```dockerfile
# mcp_servers/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Copy MCP server code
COPY mcp_servers/weather_api_server.py .
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Environment variables
ENV OPENWEATHER_API_KEY=""
ENV PORT=5000

# Expose port
EXPOSE 5000

# Run MCP server
CMD ["python", "-m", "uvicorn", "weather_api_server:app", "--host", "0.0.0.0", "--port", "5000"]
```

### GitHub Actions Deployment

```yaml
# .github/workflows/deploy-mcp.yml

name: Deploy MCP Servers

on: [push]

env:
  AZURE_RESOURCE_GROUP: azure-ai-agents
  ACR_NAME: aiagentsacr

jobs:
  build-and-push-mcp:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to ACR
        run: |
          az acr login --name ${{ env.ACR_NAME }}
      
      - name: Build MCP Weather Server
        run: |
          az acr build \
            --registry ${{ env.ACR_NAME }} \
            --image mcp-weather:latest \
            -f mcp_servers/Dockerfile \
            mcp_servers/
      
      - name: Deploy to Container Apps
        run: |
          az containerapp create \
            --name weather-mcp \
            --resource-group ${{ env.AZURE_RESOURCE_GROUP }} \
            --environment ai-agents-env \
            --image ${{ env.ACR_NAME }}.azurecr.io/mcp-weather:latest \
            --target-port 5000 \
            --env-vars \
              OPENWEATHER_API_KEY=secretref:openweather-key \
            --secrets openweather-key=${{ secrets.OPENWEATHER_API_KEY }}
```

---

## Full Integration Example

### Setup: Install MCP + Connect API

```python
# agents/orchestrator_agent/main.py

import os
import sys
from pathlib import Path
from agent_framework import Agent
from mcp.client import ClientSession
from mcp.stdio_client import StdioClientTransport

# Import local agents
sys.path.insert(0, str(Path(__file__).parent.parent))
from sql_agent.agent import root_agent as sql_agent
from retriever_agent.agent import root_agent as retriever_agent

# CONNECTION 1: Weather API via MCP
weather_mcp = ClientSession(
    transport=StdioClientTransport(
        command=[sys.executable, "-m", "mcp_servers.weather_api_server"],
        env={"OPENWEATHER_API_KEY": os.environ.get("OPENWEATHER_API_KEY")}
    )
)

# CONNECTION 2: Tourism Database via MCP
tourism_mcp = ClientSession(
    transport=StdioClientTransport(
        command=[sys.executable, "-m", "mcp_servers.tourism_database_server"],
        env={
            "EXTERNAL_SQL_SERVER": os.environ.get("TOURISM_DB_SERVER"),
            "EXTERNAL_SQL_DATABASE": os.environ.get("TOURISM_DB_NAME"),
            "EXTERNAL_SQL_USER": os.environ.get("TOURISM_DB_USER"),
            "EXTERNAL_SQL_PASSWORD": os.environ.get("TOURISM_DB_PASSWORD"),
        }
    )
)

# CONNECTION 3: News API via MCP
news_mcp = ClientSession(
    transport=StdioClientTransport(
        command=[sys.executable, "-m", "mcp_servers.news_api_server"],
        env={"NEWSAPI_KEY": os.environ.get("NEWSAPI_KEY")}
    )
)

# Create main orchestrator agent
root_agent = Agent(
    model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    name="orchestrator_agent",
    description="Comprehensive assistant with database, RAG, and external API access",
    
    # Local agents
    sub_agents=[sql_agent, retriever_agent],
    
    # External APIs via MCP
    tools=[
        # Weather API
        weather_mcp.get_tool("get_weather"),
        weather_mcp.get_tool("get_forecast"),
        
        # Tourism Database
        tourism_mcp.get_tool("query_tourism_database"),
        tourism_mcp.get_tool("get_best_season"),
        
        # News API
        news_mcp.get_tool("get_state_news"),
        news_mcp.get_tool("search_news"),
    ],
    
    instruction="""
You are a comprehensive India geography assistant with access to:

LOCAL AGENTS:
1. sql_agent → Database: countries, states, districts
2. retriever_agent → RAG: culture, history, economy

EXTERNAL APIs (MCP):
1. Weather → Current conditions, forecasts
2. Tourism Database → Attractions, best seasons
3. News → State-specific news, current events

ROUTING LOGIC:

1. LIST/META QUERIES → Use sql_agent
   "List all states" → sql_agent.list_all_states()

2. CULTURE/HISTORY QUERIES → Use retriever_agent
   "Culture of Kerala" → retriever_agent.search("Kerala culture")

3. WEATHER QUERIES → Use get_weather() or get_forecast()
   "Weather in Goa?" → get_weather("Goa")

4. TOURISM QUERIES → Use query_tourism_database()
   "Top attractions in Rajasthan?" → query_tourism_database("Rajasthan")

5. NEWS QUERIES → Use get_state_news()
   "Latest news from Maharashtra?" → get_state_news("Maharashtra")

6. COMBINED QUERIES → Use multiple tools
   "Plan trip to Kerala"
   → Use: retriever_agent + get_weather() + query_tourism_database()
   → Combine: culture info + weather + attractions → Trip plan

EXAMPLE RESPONSES:

Q: "Best time to visit Gujarat?"
A: 
   1. Call get_best_season("Gujarat") → November-February
   2. Call get_weather("Ahmedabad") → 25°C
   3. Call query_tourism_database("Gujarat") → Top 5 attractions
   → "Best time: Oct-Feb (25-28°C). Top spots: Statue of Unity, Gir Forest, Kutch..."

Q: "Tell me about Odisha's culture and current news"
A:
   1. Call retriever_agent.search("Odisha culture traditions")
   2. Call get_state_news("Odisha")
   3. Combine into single comprehensive response
"""
)

if __name__ == "__main__":
    # Run orchestrator service
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI()
    
    @app.post("/chat")
    async def chat(query: str):
        response = await root_agent.process(query)
        return {"response": response}
    
    uvicorn.run(app, host="0.0.0.0", port=8002)
```

---

## Environment Variables for MCP Integration

```yaml
# External API Keys (for MCP servers)
OPENWEATHER_API_KEY=your_openweather_api_key
NEWSAPI_KEY=your_newsapi_key

# External Database (Tourism/Attractions)
TOURISM_DB_SERVER=tourism-db.database.windows.net
TOURISM_DB_NAME=attractions
TOURISM_DB_USER=admin
TOURISM_DB_PASSWORD=secret

# Stripe (if adding payment API)
STRIPE_API_KEY=sk_test_...
STRIPE_SECRET_KEY=...

# All existing Azure service keys...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_SQL_SERVER=...
AZURE_SQL_PASSWORD=...
AZURE_SEARCH_ENDPOINT=...
AZURE_SEARCH_KEY=...
```

---

## Communication Protocols Supported

| Protocol | Pros | Cons | Use Case |
|----------|------|------|----------|
| **Stdio** | Simple, local, secure | No network | Local MCP servers |
| **TCP/HTTP** | Scalable, remote | Network overhead | Production deployments |
| **Docker Compose** | Dev friendly | Limited scaling | Local testing |
| **Kubernetes** | Highly scalable | Complex | Large deployments |

---

## Security Best Practices for MCP

```python
# ✅ GOOD: Use environment variables
@server.tool()
async def get_weather(location: str):
    api_key = os.environ["OPENWEATHER_API_KEY"]  # From secrets
    # Make API call
    
# ❌ BAD: Hardcoded API keys
@server.tool()
async def get_weather(location: str):
    api_key = "sk_live_12345..."  # EXPOSED!

# ✅ GOOD: Use managed identities
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()  # Auto-authenticates

# ✅ GOOD: Rate limiting
import time
last_call = {}

@server.tool()
async def call_api(resource: str):
    if time.time() - last_call.get(resource, 0) < 1:
        raise Exception("Rate limit: 1 call per second")
    last_call[resource] = time.time()
    # Make call
```

---

## Testing MCP Connections Locally

```bash
# Start individual MCP servers
python -m mcp_servers.weather_api_server

# In another terminal, test agent with MCP
cd agents/orchestrator_agent
python main.py

# Test queries
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Weather in Mumbai?"}'

# Response: Should call weather_mcp → OpenWeatherMap API → Return result
```

---

## Common Integration Patterns

### Pattern 1: Enrichment (Add external data to local responses)

```
User: "Tell me about Maharashtra"
  ↓
retriever_agent.search("Maharashtra") → Returns culture/history
  ↓
get_weather("Mumbai") → Returns weather
  ↓
query_tourism_database("Maharashtra") → Returns attractions
  ↓
Combine all into comprehensive response
```

### Pattern 2: Conditional Routing (Choose tool based on query)

```
User: "Compare weather in Kerala vs Goa"
  ↓
Agent detects: Multiple locations + weather
  ↓
Call get_weather("Kochi") AND get_weather("Panaji")
  ↓
Compare and return: "Kerala: 28°C, humid. Goa: 30°C, coastal breeze"
```

### Pattern 3: Multi-step Workflow (Chain MCP calls)

```
User: "Plan a trip to Rajasthan"
  ↓
Step 1: query_tourism_database("Rajasthan") → Top attractions
  ↓
Step 2: get_best_season("Rajasthan") → Oct-Feb
  ↓
Step 3: get_weather("Jaipur") → Current conditions
  ↓
Step 4: get_state_news("Rajasthan") → Current events
  ↓
Step 5: retriever_agent.search("Rajasthan culture history") → Context
  ↓
Synthesize: Complete trip itinerary + recommendations
```

---

## Troubleshooting MCP Connections

| Issue | Cause | Solution |
|-------|-------|----------|
| MCP server not connecting | Process not running | Start: `python -m mcp_servers.xxx` |
| "Tool not found" | Tool not registered | Check @server.tool() decorator |
| API timeout | External API slow | Increase timeout, implement caching |
| Authentication failed | Invalid API key | Verify environment variable |
| JSON serialization error | Response format wrong | Return dict/JSON, not custom objects |
| Rate limit exceeded | Too many calls | Implement backoff, throttling |

---

## Summary

**MCP allows agents to:**
1. ✅ Call external APIs (Weather, News, Payment, etc.)
2. ✅ Query external databases (Tourism, Products, etc.)
3. ✅ Execute workflows across multiple services
4. ✅ Maintain security with credentials in secrets
5. ✅ Scale independently with container orchestration

**Connection Pattern:**
```
Agent → MCP Client → MCP Server → External API
```

**Key Files:**
- `mcp_servers/weather_api_server.py` - MCP server definition
- `agents/orchestrator_agent/main.py` - Agent with MCP tools
- `.github/workflows/deploy-mcp.yml` - Deployment workflow
- `requirements.txt` - MCP client library

