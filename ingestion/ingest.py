"""Creates/updates a Vertex AI RAG Engine corpus from files stored in Cloud Storage.

Usage (local):
    python ingest.py

Required env vars:
    GOOGLE_CLOUD_PROJECT
    RAG_GCS_SOURCE          e.g. gs://my-bucket/docs/*

Optional env vars:
    GOOGLE_CLOUD_LOCATION       default: us-central1
    RAG_CORPUS_DISPLAY_NAME     default: adk-sample-knowledge-base
    RAG_CORPUS_ID               if set, re-use this existing corpus instead of creating
                                 a new one (id only, e.g. "4611686018427387904")
"""

import logging
import os

import vertexai
from vertexai.preview import rag

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
CORPUS_DISPLAY_NAME = os.environ.get(
    "RAG_CORPUS_DISPLAY_NAME", "adk-sample-knowledge-base"
)
RAG_CORPUS_ID = os.environ.get("RAG_CORPUS_ID")
# Note: RAG_GCS_SOURCE should be a bucket path, not a wildcard pattern
# E.g., "gs://my-bucket" or "gs://my-bucket/docs/"
# The SDK will discover all files recursively
GCS_SOURCE = os.environ["RAG_GCS_SOURCE"]


def _get_or_create_corpus() -> rag.RagCorpus:
    if RAG_CORPUS_ID:
        corpus_name = (
            f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{RAG_CORPUS_ID}"
        )
        logger.info("Re-using existing RAG corpus: %s", corpus_name)
        return rag.get_corpus(name=corpus_name)

    logger.info("Creating a new RAG corpus: %s", CORPUS_DISPLAY_NAME)
    embedding_model_config = rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-005"
    )
    # Use Serverless mode for RAG Engine (required for new projects in us-central1)
    # Serverless mode is the default; just ensure we're not specifying Spanner mode
    return rag.create_corpus(
        display_name=CORPUS_DISPLAY_NAME,
        embedding_model_config=embedding_model_config,
    )


def run_ingestion() -> str:
    """Ensures the corpus exists and imports the latest files from GCS into it."""
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    corpus = _get_or_create_corpus()

    logger.info("Importing files from %s into %s", GCS_SOURCE, corpus.name)
    rag.import_files(
        corpus_name=corpus.name,
        paths=[GCS_SOURCE],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
        max_embedding_requests_per_min=1000,
    )

    logger.info("Ingestion complete. RAG_CORPUS resource name: %s", corpus.name)
    return corpus.name


if __name__ == "__main__":
    print(f"Ingestion complete. RAG_CORPUS resource name: {run_ingestion()}")
