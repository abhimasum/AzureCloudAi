"""Model client abstraction supporting both Direct OpenAI and Azure AI Foundry.

This module provides a unified interface for LLM interactions, supporting:
- Direct OpenAI API (fallback/simple deployment)
- Azure AI Foundry (recommended, supports multi-model)

Usage:
    from core.model_client import ModelClient
    
    client = ModelClient(model="gpt-4o")
    response = await client.chat(messages=[...], temperature=0.7)
    
Environment variables:
    USE_AZURE_FOUNDRY: "true" to use Foundry, "false" for Direct OpenAI
    AZURE_FOUNDRY_ENDPOINT: https://your-region.models.ai.azure.com (Foundry only)
    AZURE_FOUNDRY_KEY: Foundry API key (Foundry only)
    OPENAI_API_KEY: Direct OpenAI API key (fallback)
    MODEL_NAME: Model to use (default: gpt-4o)
"""

import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class ModelClient:
    """Unified LLM client supporting Azure Foundry and Direct OpenAI."""
    
    def __init__(self, model: str = "gpt-4o"):
        """Initialize the model client.
        
        Args:
            model: Model name (gpt-4o, claude-3-5-sonnet, etc.)
        """
        self.model = model
        self.use_foundry = os.getenv("USE_AZURE_FOUNDRY", "false").lower() == "true"
        self.client = self._init_client()
    
    def _init_client(self) -> Any:
        """Initialize either Azure Foundry or Direct OpenAI client."""
        if self.use_foundry:
            return self._init_foundry_client()
        else:
            return self._init_openai_client()
    
    def _init_foundry_client(self) -> Any:
        """Initialize Azure AI Foundry client."""
        try:
            from azure.ai.inference import ChatCompletionsClient
            from azure.core.credentials import AzureKeyCredential
            
            endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
            key = os.getenv("AZURE_FOUNDRY_KEY")
            
            if not endpoint or not key:
                logger.warning(
                    "Azure Foundry credentials missing. Falling back to Direct OpenAI. "
                    "Set AZURE_FOUNDRY_ENDPOINT and AZURE_FOUNDRY_KEY to use Foundry."
                )
                return self._init_openai_client()
            
            logger.info(f"Using Azure AI Foundry at {endpoint}")
            return ChatCompletionsClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )
        except ImportError:
            logger.warning("azure-ai-inference not installed. Falling back to Direct OpenAI.")
            return self._init_openai_client()
        except Exception as e:
            logger.warning(f"Failed to initialize Foundry client: {e}. Falling back to Direct OpenAI.")
            return self._init_openai_client()
    
    def _init_openai_client(self) -> Any:
        """Initialize Direct OpenAI client."""
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        logger.info("Using Direct OpenAI API")
        return OpenAI(api_key=api_key)
    
    async def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Any:
        """Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters passed to the API
            
        Returns:
            Response from the LLM
        """
        try:
            if self.use_foundry and hasattr(self.client, 'complete'):
                # Azure Foundry SDK
                response = self.client.complete(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return response
            else:
                # Direct OpenAI
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return response
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise


class EmbeddingClient:
    """Unified embedding client supporting Azure Foundry and Direct OpenAI."""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """Initialize the embedding client.
        
        Args:
            model: Embedding model name
        """
        self.model = model
        self.use_foundry = os.getenv("USE_AZURE_FOUNDRY", "false").lower() == "true"
        self.client = self._init_client()
    
    def _init_client(self) -> Any:
        """Initialize either Azure Foundry or Direct OpenAI client."""
        if self.use_foundry:
            return self._init_foundry_client()
        else:
            return self._init_openai_client()
    
    def _init_foundry_client(self) -> Any:
        """Initialize Azure AI Foundry client."""
        try:
            from azure.ai.inference import EmbeddingsClient
            from azure.core.credentials import AzureKeyCredential
            
            endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
            key = os.getenv("AZURE_FOUNDRY_KEY")
            
            if not endpoint or not key:
                logger.warning("Azure Foundry credentials missing. Falling back to Direct OpenAI.")
                return self._init_openai_client()
            
            logger.info(f"Using Azure AI Foundry embeddings at {endpoint}")
            return EmbeddingsClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )
        except ImportError:
            logger.warning("azure-ai-inference not installed. Falling back to Direct OpenAI.")
            return self._init_openai_client()
        except Exception as e:
            logger.warning(f"Failed to initialize Foundry embeddings: {e}. Falling back to Direct OpenAI.")
            return self._init_openai_client()
    
    def _init_openai_client(self) -> Any:
        """Initialize Direct OpenAI client."""
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        logger.info("Using Direct OpenAI embeddings")
        return OpenAI(api_key=api_key)
    
    def embed(self, text: str) -> list[float]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            if self.use_foundry and hasattr(self.client, 'embed'):
                # Azure Foundry SDK
                response = self.client.embed(
                    model=self.model,
                    input=text
                )
                # Foundry returns data[0].embedding
                return response.data[0].embedding
            else:
                # Direct OpenAI
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536  # text-embedding-3-small dimension
