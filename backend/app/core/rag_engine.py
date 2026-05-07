"""
RAG (Retrieval-Augmented Generation) Engine.

This is the main orchestrator that ties together:
  1. Vector store (retrieval)
  2. LLM client (generation)
  3. Source citation formatting
  4. Confidence scoring + escalation

The pipeline:
  Query → Embed → Retrieve top-k chunks → Build context → LLM generates answer → Format with citations
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from app.config import settings
from app.core.vector_store import VectorStore
from app.core.llm_client import get_llm_client, BaseLLMClient, LLMResponse
from app.core.document_processor import process_document

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Complete response from the RAG pipeline."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    needs_escalation: bool
    model_used: str
    tokens_used: int
    chunks_retrieved: int


@dataclass
class IngestionResult:
    """Result of ingesting a document."""
    filename: str
    chunks_created: int
    doc_id: str
    department: str
    success: bool
    error: Optional[str] = None


class RAGEngine:
    """
    Main RAG pipeline orchestrator.

    Usage:
        engine = RAGEngine()
        # Ingest a document
        result = engine.ingest_document("path/to/policy.pdf", department="hr")
        # Query
        response = engine.query("What is our PTO policy?", department="hr")
    """

    def __init__(
        self,
        vector_store: VectorStore = None,
        llm_client: BaseLLMClient = None,
    ):
        self._vector_store = vector_store or VectorStore()
        self._llm = llm_client or get_llm_client()
        logger.info("RAGEngine initialized")

    def ingest_document(
        self,
        file_path: str,
        department: str = "general",
        doc_id: Optional[str] = None,
    ) -> IngestionResult:
        """
        Full ingestion pipeline: parse → chunk → embed → store.

        Args:
            file_path: Path to document file (PDF, DOCX, or TXT)
            department: Department tag for RBAC
            doc_id: Optional unique ID (defaults to filename)
        """
        try:
            # 1. Parse and chunk
            chunks = process_document(file_path, department=department, doc_id=doc_id)
            if not chunks:
                return IngestionResult(
                    filename=file_path, chunks_created=0,
                    doc_id=doc_id or file_path, department=department,
                    success=False, error="No chunks extracted",
                )

            # 2. Embed and store
            stored = self._vector_store.add_chunks(chunks)

            return IngestionResult(
                filename=file_path,
                chunks_created=stored,
                doc_id=doc_id or chunks[0].metadata.get("doc_id", file_path),
                department=department,
                success=True,
            )
        except Exception as e:
            logger.error(f"Ingestion failed for {file_path}: {e}")
            return IngestionResult(
                filename=file_path, chunks_created=0,
                doc_id=doc_id or file_path, department=department,
                success=False, error=str(e),
            )

    def query(
        self,
        question: str,
        department: Optional[str] = None,
        departments: Optional[List[str]] = None,
        top_k: int = None,
        llm_provider: Optional[str] = None,
    ) -> RAGResponse:
        """
        Full RAG query pipeline: embed query → retrieve → generate answer.

        Args:
            question: The user's question
            department: Department filter for RBAC (single)
            departments: Department filter for RBAC (multiple, for admins)
            top_k: Override number of chunks to retrieve
        """
        # 1. Retrieve relevant chunks
        results = self._vector_store.search(
            query=question,
            top_k=top_k or settings.TOP_K_RESULTS,
            department=department,
            departments=departments,
        )

        if not results:
            return RAGResponse(
                answer="I couldn't find any relevant information in the knowledge base for your question. "
                       "Please try rephrasing or contact your department administrator.",
                sources=[],
                confidence=0.0,
                needs_escalation=True,
                model_used="none",
                tokens_used=0,
                chunks_retrieved=0,
            )

        # 2. Build context from retrieved chunks
        context = self._build_context(results)

        # 3. Extract source information for citation
        sources = self._extract_sources(results)

        # 4. Generate answer with LLM
        if llm_provider:
            from app.core.llm_client import get_llm_client_by_provider
            llm = get_llm_client_by_provider(llm_provider)
        else:
            llm = self._llm

        llm_response = llm.generate(question, context)

        # 5. Determine if escalation is needed
        needs_escalation = (
            llm_response.confidence < settings.CONFIDENCE_THRESHOLD
            or results[0]["score"] < settings.CONFIDENCE_THRESHOLD
        )

        return RAGResponse(
            answer=llm_response.content,
            sources=sources,
            confidence=llm_response.confidence,
            needs_escalation=needs_escalation,
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
            chunks_retrieved=len(results),
        )

    async def aquery(
        self,
        question: str,
        department: Optional[str] = None,
        departments: Optional[List[str]] = None,
        top_k: int = None,
        llm_provider: Optional[str] = None,
    ) -> RAGResponse:
        """Async version of query for FastAPI endpoints."""
        results = self._vector_store.search(
            query=question,
            top_k=top_k or settings.TOP_K_RESULTS,
            department=department,
            departments=departments,
        )

        if not results:
            return RAGResponse(
                answer="I couldn't find any relevant information in the knowledge base.",
                sources=[], confidence=0.0, needs_escalation=True,
                model_used="none", tokens_used=0, chunks_retrieved=0,
            )

        context = self._build_context(results)
        sources = self._extract_sources(results)
        
        if llm_provider:
            from app.core.llm_client import get_llm_client_by_provider
            llm = get_llm_client_by_provider(llm_provider)
        else:
            llm = self._llm

        llm_response = await llm.agenerate(question, context)

        needs_escalation = (
            llm_response.confidence < settings.CONFIDENCE_THRESHOLD
            or results[0]["score"] < settings.CONFIDENCE_THRESHOLD
        )

        return RAGResponse(
            answer=llm_response.content, sources=sources,
            confidence=llm_response.confidence,
            needs_escalation=needs_escalation,
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
            chunks_retrieved=len(results),
        )

    def _build_context(self, results: List[Dict]) -> str:
        """
        Build a formatted context string from retrieved chunks.
        Includes source info so the LLM can cite properly.
        """
        context_parts = []
        total_len = 0

        for i, r in enumerate(results):
            source = r["metadata"].get("source", "Unknown")
            page = r["metadata"].get("page", "N/A")
            dept = r["metadata"].get("department", "general")

            header = f"[Document: {source} | Page: {page} | Department: {dept}]"
            chunk_text = f"{header}\n{r['content']}"

            # Respect max context length
            if total_len + len(chunk_text) > settings.MAX_CONTEXT_LENGTH:
                break

            context_parts.append(chunk_text)
            total_len += len(chunk_text)

        return "\n\n---\n\n".join(context_parts)

    def _extract_sources(self, results: List[Dict]) -> List[Dict]:
        """Extract unique source documents from results."""
        seen = set()
        sources = []
        for r in results:
            source_key = (
                r["metadata"].get("source", "Unknown"),
                r["metadata"].get("page", "N/A"),
            )
            if source_key not in seen:
                seen.add(source_key)
                sources.append({
                    "document": r["metadata"].get("source", "Unknown"),
                    "page": r["metadata"].get("page", "N/A"),
                    "department": r["metadata"].get("department", "general"),
                    "relevance_score": r["score"],
                })
        return sources

    def delete_document(self, doc_id: str) -> int:
        """Remove a document from the vector store."""
        return self._vector_store.delete_document(doc_id)

    def get_documents(self) -> List[Dict]:
        """List all documents in the knowledge base."""
        return self._vector_store.get_document_list()

    @property
    def total_chunks(self) -> int:
        return self._vector_store.total_chunks
