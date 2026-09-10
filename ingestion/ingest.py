"""Ingests documents into Azure AI Search index using Azure OpenAI embeddings.

Usage (local):
    python ingest.py

Required env vars:
    AZURE_STORAGE_ACCOUNT_NAME     e.g. aiagentsstorageabhimasum
    AZURE_STORAGE_ACCOUNT_KEY      Storage account key
    AZURE_STORAGE_CONTAINER        e.g. documents

Azure AI Search env vars:
    AZURE_SEARCH_ENDPOINT          e.g. https://mysearch.search.windows.net
    AZURE_SEARCH_KEY               Search service API key
    AZURE_SEARCH_INDEX             e.g. documents (created if not exists)

Azure OpenAI env vars:
    AZURE_OPENAI_ENDPOINT          e.g. https://myresource.openai.azure.com
    AZURE_OPENAI_API_KEY           OpenAI API key
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT   e.g. text-embedding-3-small
"""

import logging
import os
from pathlib import Path

from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI, OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure Storage
STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "aiagentabhimasum2storage")
STORAGE_KEY = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER", "documents")

# Azure AI Search
SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY")
SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX", "documents")

# Azure OpenAI (for embeddings)
OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
OPENAI_EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")


def _create_or_get_index():
    """Create or verify Azure AI Search index exists."""
    if not SEARCH_ENDPOINT or not SEARCH_KEY:
        logger.warning("Azure AI Search not configured - skipping index creation")
        return

    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(SEARCH_KEY))

    # Check if index already exists
    try:
        existing_index = index_client.get_index(SEARCH_INDEX)
        logger.info(f"Index '{SEARCH_INDEX}' already exists")
        return
    except Exception:
        pass  # Index doesn't exist, create it

    # Define the search index with vector search capabilities
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="chunk_id", type=SearchFieldDataType.String),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="myHnswProfile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
        profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")],
    )

    # Create simple index without semantic search (API compatibility)
    index = SearchIndex(
        name=SEARCH_INDEX,
        fields=fields,
        vector_search=vector_search,
    )

    try:
        result = index_client.create_or_update_index(index)
        logger.info(f"Index '{result.name}' created successfully (without semantic search)")
    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        raise


def _get_documents_from_storage() -> list[dict]:
    """Read documents from Azure Storage."""
    if not STORAGE_ACCOUNT or not STORAGE_KEY:
        logger.warning("Azure Storage not configured - using sample documents from data/")
        docs = []
        data_path = Path(__file__).parent.parent / "data" / "sample_docs"
        if data_path.exists():
            for file in data_path.glob("*.md"):
                with open(file, "r", encoding="utf-8") as f:
                    docs.append({
                        "title": file.stem,
                        "content": f.read(),
                        "source": file.name,
                    })
        return docs

    blob_client = BlobServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=STORAGE_KEY
    )
    container_client = blob_client.get_container_client(STORAGE_CONTAINER)

    docs = []
    for blob in container_client.list_blobs():
        blob_download = container_client.download_blob(blob.name)
        content = blob_download.readall().decode("utf-8")
        docs.append({
            "title": blob.name.replace(".md", "").replace("_", " "),
            "content": content,
            "source": blob.name,
        })
    return docs


def _generate_embeddings(text: str) -> list[float]:
    """Generate embeddings using Azure OpenAI or Direct OpenAI (fallback)."""
    # Try Azure OpenAI first
    if OPENAI_ENDPOINT and OPENAI_KEY:
        try:
            client = AzureOpenAI(
                api_key=OPENAI_KEY,
                api_version="2024-02-15-preview",
                azure_endpoint=OPENAI_ENDPOINT
            )
            response = client.embeddings.create(
                input=text,
                model=OPENAI_EMBEDDING_DEPLOYMENT
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Azure OpenAI embedding failed: {e}, falling back to Direct OpenAI")
    
    # Fallback to Direct OpenAI
    direct_api_key = os.environ.get("OPENAI_API_KEY")
    if direct_api_key:
        try:
            client = OpenAI(api_key=direct_api_key)
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-small"  # More cost-effective
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Direct OpenAI embedding failed: {e}")
    
    logger.warning("No embedding service configured - using zero embeddings (search will not work)")
    return [0.0] * 1536


def run_ingestion() -> str:
    """Ingests documents into Azure AI Search."""
    logger.info("Starting document ingestion into Azure AI Search")

    # Create index
    _create_or_get_index()

    # Get documents
    documents = _get_documents_from_storage()
    logger.info(f"Found {len(documents)} documents to index")

    if not documents:
        logger.warning("No documents found to ingest")
        return SEARCH_INDEX

    # Upload to search index
    if not SEARCH_ENDPOINT or not SEARCH_KEY:
        logger.warning("Azure AI Search not configured - skipping upload")
        return SEARCH_INDEX

    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX,
        credential=AzureKeyCredential(SEARCH_KEY)
    )

    # Chunk documents and add embeddings
    docs_to_upload = []
    chunk_size = 1000
    chunk_overlap = 100

    for doc in documents:
        content = doc["content"]
        title = doc["title"]

        # Simple chunking
        for i in range(0, len(content), chunk_size - chunk_overlap):
            chunk = content[i : i + chunk_size]
            chunk_id = f"{title}-chunk-{i // (chunk_size - chunk_overlap)}"

            embedding = _generate_embeddings(chunk)

            docs_to_upload.append({
                "id": chunk_id.replace(" ", "-"),
                "title": title,
                "content": chunk,
                "chunk_id": chunk_id,
                "embedding": embedding,
            })

    # Upload in batches
    batch_size = 10
    for i in range(0, len(docs_to_upload), batch_size):
        batch = docs_to_upload[i : i + batch_size]
        try:
            result = search_client.upload_documents(batch)
            logger.info(f"Uploaded {len(result)} documents (batch {i // batch_size + 1})")
        except Exception as e:
            logger.error(f"Failed to upload batch: {e}")

    logger.info(f"Ingestion complete. Total documents indexed: {len(docs_to_upload)} chunks")
    return SEARCH_INDEX


if __name__ == "__main__":
    print(f"Ingestion complete. Search index: {run_ingestion()}")
