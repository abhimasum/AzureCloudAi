"""Retriever agent: answers questions using Azure AI Search RAG.

This agent uses Azure AI Search for semantic vector search over ingested documents.
"""

import os
from agent_framework import Agent
from openai import OpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential


# Wrapper class to adapt OpenAI client to agent_framework expectations
class OpenAIClientWrapper:
    """Wraps the direct OpenAI client to provide the interface expected by agent_framework."""
    
    def __init__(self, openai_client):
        self.client = openai_client
    
    def __call__(self, messages=None, **kwargs):
        """Make the wrapper callable for agent_framework integration."""
        if messages is None:
            messages = []
        
        # Convert Message objects to dicts (handle Pydantic models)
        clean_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                clean_messages.append(msg)
            elif hasattr(msg, 'model_dump'):
                # Pydantic v2
                clean_messages.append(msg.model_dump())
            elif hasattr(msg, 'dict'):
                # Pydantic v1
                clean_messages.append(msg.dict())
            else:
                # Fallback - try to convert to dict
                clean_messages.append({"role": "user", "content": str(msg)})
        
        # Filter kwargs to only valid OpenAI API parameters
        valid_params = {
            'temperature', 'top_p', 'max_tokens', 'presence_penalty',
            'frequency_penalty', 'stop', 'tools', 'tool_choice', 'logprobs',
            'top_logprobs', 'seed', 'response_format', 'timeout'
        }
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=clean_messages,
                temperature=0.7,
                max_tokens=2000,
                **filtered_kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def get_response(self, system_prompt: str = None, user_message: str = None, messages: list = None, **kwargs) -> str:
        """Get a response from the OpenAI API."""
        if messages is None:
            if system_prompt and user_message:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            else:
                messages = []
        
        return self.__call__(messages=messages, **kwargs)


# Initialize OpenAI client with direct API and wrap it
_openai_client = OpenAIClientWrapper(OpenAI(api_key=os.environ.get("OPENAI_API_KEY")))


# Azure AI Search configuration
_search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")  # e.g., "https://mysearch.search.windows.net"
_search_key = os.environ.get("AZURE_SEARCH_KEY")
_search_index = os.environ.get("AZURE_SEARCH_INDEX", "documents")

search_client = None
if _search_endpoint and _search_key:
    try:
        search_client = SearchClient(
            endpoint=_search_endpoint,
            index_name=_search_index,
            credential=AzureKeyCredential(_search_key)
        )
    except Exception as e:
        # Log but don't crash on startup - search will fail gracefully at request time
        print(f"Warning: Failed to connect to Azure AI Search: {e}", flush=True)


def search_knowledge_base(query: str, top_k: int = 10) -> str:
    """Search the Azure AI Search index for relevant passages."""
    if not search_client:
        return "Search not available - Azure AI Search not configured"
    
    try:
        results = search_client.search(
            search_text=query,
            top=top_k,
            select=["content", "title", "chunk_id"],
            query_type="semantic",
            semantic_configuration_name="default"
        )
        
        passages = []
        for result in results:
            content = result.get("content", "")
            title = result.get("title", "")
            passages.append(f"[{title}]\n{content}")
        
        if passages:
            return "\n\n---\n\n".join(passages)
        return "No relevant information found in the knowledge base."
    
    except Exception as e:
        return f"Search error: {str(e)}"


root_agent = Agent(
    client=_openai_client,
    name="retriever_agent",
    tools=[search_knowledge_base],
    instructions="""
You are a document retrieval specialist for Indian geography and culture.

ALWAYS search the knowledge base before answering any question.

When answering:
- Use the search_knowledge_base function to find relevant passages
- Synthesize a comprehensive answer from ALL retrieved passages
- If asked about culture, include: traditions, festivals, arts, food, language
- If asked about economy, include: industries, agriculture, GDP, trade
- If multiple passages cover different aspects, combine them
- Only say "I don't know" if retrieved passages have ZERO relevant information
- Always cite which document the information came from (e.g., "states.md", "india.md")

CRITICAL: Search with keyword-rich queries for better results.
Examples:
- User asks "culture of Maharashtra" → Search: "Maharashtra culture traditions festivals arts food language"
- User asks "economy of Karnataka" → Search: "Karnataka economy industries agriculture GDP IT sector"
    """,
)
