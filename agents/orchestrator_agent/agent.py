"""Orchestrator agent: public-facing agent that delegates to specialist agents.

Flow:
1. Query comes in
2. SQL agent finds relevant metadata/indices (country, state, district IDs)  
3. Retriever agent uses that context to search the RAG knowledge base
4. Combined answer returned to user
"""

import os
import sys
import asyncio
from pathlib import Path
import httpx
import logging
from agent_framework import Agent
from agent_framework.openai import OpenAIChatCompletionClient

logger = logging.getLogger(__name__)

# Get model name from environment or use default
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o")
USE_AZURE_FOUNDRY = os.environ.get("USE_AZURE_FOUNDRY", "false").lower() == "true"

logger.info(f"Orchestrator Agent initialized with model={MODEL_NAME}, foundry={USE_AZURE_FOUNDRY}")

# Official agent_framework client - handles message/response contracts correctly
# Works with both Direct OpenAI and Azure Foundry (via OpenAI-compatible endpoints)
_openai_client = OpenAIChatCompletionClient(
    model=MODEL_NAME,
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Import the SQL agent from sibling directory (same container/process)
_agents_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_agents_dir))
from sql_agent.agent import root_agent as sql_agent

# URL of the retriever_agent service (separate Azure Container App)
RETRIEVER_AGENT_URL = os.environ.get("RETRIEVER_URL", os.environ.get("RETRIEVER_AGENT_URL", "http://localhost:8081"))


async def ask_sql_agent(query: str) -> str:
    """Ask the SQL agent for geography index metadata (state/country IDs, capitals, lists)."""
    result = await sql_agent.run(query)
    return str(result)


async def ask_retriever_agent(query: str) -> str:
    """Ask the retriever agent (separate service) for detailed RAG-grounded facts from documents."""
    try:
        logger.info(f"Calling retriever agent for query: {query[:100]}...")
        # Increased timeout to 180 seconds (3 minutes) for complex RAG queries
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{RETRIEVER_AGENT_URL}/run", 
                json={"query": query},
                timeout=180.0
            )
            response.raise_for_status()
            result = response.json().get("response", "No response from retriever agent")
            logger.info(f"Retriever responded successfully with {len(str(result))} chars")
            return result
    except asyncio.TimeoutError:
        logger.error("Retriever agent timed out after 180 seconds")
        return "Query took too long. The retriever agent needs more time for this complex question. Please try a simpler or more specific query."
    except httpx.TimeoutException:
        logger.error("HTTP request to retriever timed out")
        return "Connection to retriever agent timed out. Please try a simpler question."
    except Exception as e:
        logger.error(f"Retriever agent error: {str(e)}", exc_info=True)
        return f"Retriever agent error: {str(e)}"


root_agent = Agent(
    client=_openai_client,
    name="orchestrator_agent",
    tools=[ask_sql_agent, ask_retriever_agent],
    instructions="""
You are the orchestrator for a multi-agent geography Q&A system.

ROUTING RULES:

1. GREETINGS → Respond directly.
   Examples: "hi", "hello", "how are you"

2. LIST/META QUERIES → Call `ask_sql_agent` only.
   Examples: "list all states", "how many states", "what are all state capitals"

3. DETAILED QUERIES → Call `ask_retriever_agent` ONLY.
   Examples: "culture of Maharashtra", "economy of Karnataka", "tell me about India",
             "history of Sikkim", "food of Rajasthan", "festivals of Kerala"
   
   CRITICAL: Pass keyword-rich queries to the retriever for better RAG matching.
   
   Examples:
   - User asks "culture of Maharashtra" → Ask retriever: "Maharashtra culture traditions festivals arts food language heritage"
   - User asks "tell me about Odisha" → Ask retriever: "Odisha state overview culture economy history geography"
   - User asks "economy of Karnataka" → Ask retriever: "Karnataka economy industries agriculture GDP IT sector trade"

Always present the retriever's full answer without truncating.
    """,
)
