"""Orchestrator agent: public-facing agent that delegates to specialist agents.

Flow:
1. Query comes in
2. SQL agent finds relevant metadata/indices (country, state, district IDs)  
3. Retriever agent uses that context to search the RAG knowledge base
4. Combined answer returned to user
"""

import os
import sys
from pathlib import Path
from agent_framework import Agent


# Import the SQL agent from sibling directory
_agents_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_agents_dir))
from sql_agent.agent import root_agent as sql_agent

# URL of the retriever_agent service (Azure Container App URL)
RETRIEVER_AGENT_URL = os.environ.get("RETRIEVER_AGENT_URL", "http://localhost:8081")

# TODO: Configure remote retriever agent using MAF's A2A protocol
# For now, this is a placeholder for the remote agent
retriever_agent = Agent(
    name="retriever_agent",
    description=(
        "Specialist agent with access to Azure AI Search RAG index. "
        "Delegate to it for any question that needs grounded facts from documents."
    ),
)

root_agent = Agent(
    model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    name="orchestrator_agent",
    description="Front-door assistant that routes requests to specialist agents.",
    instruction="""
You are the orchestrator for a multi-agent geography Q&A system.

ROUTING RULES:

1. GREETINGS → Respond directly.
   Examples: "hi", "hello", "how are you"

2. LIST/META QUERIES → Delegate to `sql_agent` only.
   Examples: "list all states", "how many states", "what are all state capitals"

3. DETAILED QUERIES → Delegate to `retriever_agent` ONLY.
   Examples: "culture of Maharashtra", "economy of Karnataka", "tell me about India",
             "history of Sikkim", "food of Rajasthan", "festivals of Kerala"
   
   CRITICAL: Pass keyword-rich queries to the retriever for better RAG matching.
   
   Examples:
   - User asks "culture of Maharashtra" → Ask retriever: "Maharashtra culture traditions festivals arts food language heritage"
   - User asks "tell me about Odisha" → Ask retriever: "Odisha state overview culture economy history geography"
   - User asks "economy of Karnataka" → Ask retriever: "Karnataka economy industries agriculture GDP IT sector trade"

Always present the retriever's full answer without truncating.
    """,
    sub_agents=[sql_agent, retriever_agent],
)
