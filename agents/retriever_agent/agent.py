"""Retriever agent: answers questions using Azure AI Search RAG.

This agent uses Azure AI Search for semantic vector search over ingested documents.
"""

import os
from agent_framework import Agent
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential


# Azure AI Search configuration
_search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")  # e.g., "https://mysearch.search.windows.net"
_search_key = os.environ.get("AZURE_SEARCH_KEY")
_search_index = os.environ.get("AZURE_SEARCH_INDEX", "geography-docs")

search_client = SearchClient(
    endpoint=_search_endpoint,
    index_name=_search_index,
    credential=AzureKeyCredential(_search_key)
) if _search_endpoint and _search_key else None


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
    model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    name="retriever_agent",
    description=(
        "Specialist agent that answers questions using Azure AI Search. "
        "Searches the document knowledge base for detailed information."
    ),
    instruction="""
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
