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
import httpx
from agent_framework import Agent
from openai import OpenAI


# Wrapper class to adapt OpenAI client to agent_framework expectations
class OpenAIClientWrapper:
    """Wraps the direct OpenAI client to provide the interface expected by agent_framework."""
    
    def __init__(self, openai_client):
        self.client = openai_client
    
    def get_response(self, system_prompt: str, user_message: str, **kwargs) -> str:
        """Get a response from the OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=2000,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


# Initialize OpenAI client with direct API and wrap it
_openai_client = OpenAIClientWrapper(OpenAI(api_key=os.environ.get("OPENAI_API_KEY")))

# Import the SQL agent from sibling directory (same container/process)
_agents_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_agents_dir))
from sql_agent.agent import root_agent as sql_agent

# URL of the retriever_agent service (separate Azure Container App)
RETRIEVER_AGENT_URL = os.environ.get("RETRIEVER_AGENT_URL", "http://localhost:8081")


async def ask_sql_agent(query: str) -> str:
    """Ask the SQL agent for geography index metadata (state/country IDs, capitals, lists)."""
    result = await sql_agent.run(query)
    return str(result)


async def ask_retriever_agent(query: str) -> str:
    """Ask the retriever agent (separate service) for detailed RAG-grounded facts from documents."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{RETRIEVER_AGENT_URL}/run", json={"query": query})
            response.raise_for_status()
            return response.json().get("response", "No response from retriever agent")
    except Exception as e:
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
