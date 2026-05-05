"""
Embedding model abstraction layer.

Supports:
  - sentence-transformers (local, free) — DEFAULT
  - OpenAI text-embedding-3-small (API, paid)

Design decision: We default to sentence-transformers/all-MiniLM-L6-v2 because:
  1. It's completely free (runs locally)
  2. 384-dimensional vectors are small and fast
  3. Quality is sufficient for internal document retrieval
  4. No API rate limits or costs

The abstraction allows swapping to OpenAI embeddings later if needed.
"""

import logging
from typing import List
from abc import ABC, abstractmethod
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings, EmbeddingProvider

logger = logging.getLogger(__name__)


class BaseEmbedding(ABC):
    """Abstract base for all embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        ...

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts for efficiency."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...


class SentenceTransformerEmbedding(BaseEmbedding):
    """
    Local embedding using sentence-transformers.

    Model: all-MiniLM-L6-v2
    - 384 dimensions
    - ~80MB model size
    - Fast inference on CPU
    - Good quality for semantic search
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        logger.info(f"Loading sentence-transformer model: {self.model_name}")
        self._model = SentenceTransformer(self.model_name)
        # sentence-transformers v4 uses get_sentence_embedding_dimension()
        if hasattr(self._model, "get_sentence_embedding_dimension"):
            self._dimension = self._model.get_sentence_embedding_dimension()
        else:
            self._dimension = self._model.get_embedding_dimension()
        logger.info(f"Model loaded. Dimension: {self._dimension}")

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text. Returns a list of floats."""
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts in one call (much faster than looping).

        sentence-transformers handles batching internally, so this is
        significantly more efficient than calling embed_text() in a loop.
        """
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=len(texts) > 100,
        )
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension


class OpenAIEmbedding(BaseEmbedding):
    """
    OpenAI embedding using text-embedding-3-small.

    Requires OPENAI_API_KEY in environment.
    - 1536 dimensions
    - $0.02 per 1M tokens
    - Higher quality but costs money
    """

    def __init__(self):
        from openai import OpenAI

        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._dimension = 1536
        self._model = "text-embedding-3-small"
        logger.info(f"OpenAI embedding initialized: {self._model}")

    def embed_text(self, text: str) -> List[float]:
        response = self._client.embeddings.create(
            input=text,
            model=self._model,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        # OpenAI supports batch embedding natively
        response = self._client.embeddings.create(
            input=texts,
            model=self._model,
        )
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        return self._dimension


@lru_cache(maxsize=1)
def get_embedding_model() -> BaseEmbedding:
    """
    Factory function: returns the configured embedding model.

    Usage:
        embedder = get_embedding_model()
        vector = embedder.embed_text("Hello world")
    """
    if settings.EMBEDDING_PROVIDER == EmbeddingProvider.OPENAI:
        return OpenAIEmbedding()
    else:
        return SentenceTransformerEmbedding()
