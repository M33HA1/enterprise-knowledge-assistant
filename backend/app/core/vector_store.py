"""
ChromaDB vector store wrapper.

Handles storing and retrieving document chunk embeddings.
Department metadata enables RBAC-filtered searches.

Design decisions:
  - ChromaDB in persistent mode (data survives restarts)
  - Department stored as metadata on each chunk for filtering
  - Cosine similarity (default for normalized embeddings)
  - Batch upsert for efficient ingestion
"""

import logging
import os
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.core.embeddings import BaseEmbedding, get_embedding_model
from app.core.document_processor import DocumentChunk

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB-backed vector store for document chunks.

    Supports:
      - Adding chunks with embeddings and metadata
      - Similarity search with optional department filtering (RBAC)
      - Deleting documents by doc_id
      - Listing stored documents
    """

    def __init__(self, embedding_model: BaseEmbedding = None):
        self._embedding = embedding_model or get_embedding_model()

        # Ensure persist directory exists
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self._client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Get or create the collection
        self._collection = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"VectorStore initialized. Collection: {settings.CHROMA_COLLECTION_NAME}, "
            f"Existing docs: {self._collection.count()}"
        )

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        Embed and store document chunks in ChromaDB.

        Returns the number of chunks added.
        """
        if not chunks:
            return 0

        # Prepare data for batch upsert
        texts = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [
            f"{chunk.metadata.get('doc_id', 'unknown')}_{chunk.metadata.get('chunk_index', i)}"
            for i, chunk in enumerate(chunks)
        ]

        # Batch embed
        logger.info(f"Embedding {len(texts)} chunks...")
        embeddings = self._embedding.embed_batch(texts)

        # Upsert into ChromaDB
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info(f"Stored {len(chunks)} chunks. Total in collection: {self._collection.count()}")
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = None,
        department: Optional[str] = None,
        departments: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks using semantic similarity.

        Args:
            query: The search query text
            top_k: Number of results to return
            department: Single department filter (RBAC)
            departments: Multiple departments filter (for admins)

        Returns:
            List of dicts with keys: content, metadata, score
        """
        top_k = top_k or settings.TOP_K_RESULTS
        query_embedding = self._embedding.embed_text(query)

        # Build department filter for RBAC
        where_filter = None
        if department:
            where_filter = {"department": department}
        elif departments:
            where_filter = {"department": {"$in": departments}}

        # Query ChromaDB
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                # ChromaDB returns cosine distance; convert to similarity
                similarity = 1 - dist
                formatted.append({
                    "content": doc,
                    "metadata": meta,
                    "score": round(similarity, 4),
                })

        return formatted

    def delete_document(self, doc_id: str) -> int:
        """Delete all chunks for a given document ID."""
        # Get IDs of chunks belonging to this document
        results = self._collection.get(
            where={"doc_id": doc_id},
            include=[],
        )
        if results["ids"]:
            self._collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks for doc: {doc_id}")
            return len(results["ids"])
        return 0

    def get_document_list(self) -> List[Dict[str, Any]]:
        """Get a list of unique documents in the store."""
        all_metadata = self._collection.get(include=["metadatas"])
        docs = {}
        for meta in all_metadata["metadatas"]:
            doc_id = meta.get("doc_id", "unknown")
            if doc_id not in docs:
                docs[doc_id] = {
                    "doc_id": doc_id,
                    "source": meta.get("source", "unknown"),
                    "department": meta.get("department", "general"),
                    "file_type": meta.get("file_type", "unknown"),
                    "total_pages": meta.get("total_pages", 0),
                    "chunk_count": 0,
                }
            docs[doc_id]["chunk_count"] += 1
        return list(docs.values())

    @property
    def total_chunks(self) -> int:
        return self._collection.count()
