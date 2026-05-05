"""
RAG pipeline tests — document processing and embeddings.

Pytest-compatible tests cover the parts that work without an LLM API key:
  - Document parsing and chunking (test_document_processing)
  - Embedding model (test_embeddings)

The full pipeline (vector store + LLM generation) requires API keys and is
available as a standalone script:
  python -m tests.run_rag_pipeline          # embedding-only
  python -m tests.run_rag_pipeline --full   # full pipeline (needs LLM key)
"""

import os
import sys
import logging
from pathlib import Path

import pytest

# ─── Setup logging ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_rag")

# ─── Paths ────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = BACKEND_DIR / "tests" / "sample_data"

HR_DOC = SAMPLE_DIR / "employee_handbook.txt"
ENG_DOC = SAMPLE_DIR / "engineering_guidelines.txt"


# ─── Pytest-compatible tests (no API key required) ────────────

def test_document_processing():
    """Parse and chunk documents — no API key required."""
    from app.core.document_processor import DocumentParser, DocumentChunker

    parser = DocumentParser()
    chunker = DocumentChunker()

    # Parse HR handbook
    parsed = parser.parse(str(HR_DOC))
    assert parsed.filename == "employee_handbook.txt"
    assert parsed.file_type == "txt"
    assert len(parsed.content) > 0

    chunks = chunker.chunk_document(parsed, department="hr", doc_id="hr_handbook_v3.2")
    assert len(chunks) > 0
    assert chunks[0].metadata["department"] == "hr"
    assert chunks[0].metadata["doc_id"] == "hr_handbook_v3.2"

    # Parse engineering doc
    parsed_eng = parser.parse(str(ENG_DOC))
    chunks_eng = chunker.chunk_document(parsed_eng, department="engineering", doc_id="eng_guidelines_v2.1")
    assert len(chunks_eng) > 0
    assert chunks_eng[0].metadata["department"] == "engineering"


def test_embeddings():
    """Embedding model produces correct-dimension vectors — no API key required."""
    from app.core.embeddings import get_embedding_model

    embedder = get_embedding_model()
    assert embedder.dimension == 384

    vec = embedder.embed_text("What is the PTO policy?")
    assert len(vec) == 384

    texts = [
        "paid time off vacation days",
        "remote work from home policy",
        "code review requirements",
    ]
    vecs = embedder.embed_batch(texts)
    assert len(vecs) == 3
    assert all(len(v) == 384 for v in vecs)


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") and
    not os.environ.get("ANTHROPIC_API_KEY") and
    not os.environ.get("GEMINI_API_KEY"),
    reason="No LLM API key set — skipping vector store + RAG tests",
)
def test_vector_store_and_rag():
    """Vector store + RAG pipeline — requires an LLM API key."""
    from app.core.document_processor import DocumentParser, DocumentChunker
    from app.core.vector_store import VectorStore
    from app.core.rag_engine import RAGEngine

    parser = DocumentParser()
    chunker = DocumentChunker()

    hr_chunks = chunker.chunk_document(
        parser.parse(str(HR_DOC)), department="hr", doc_id="hr_handbook_v3.2"
    )
    eng_chunks = chunker.chunk_document(
        parser.parse(str(ENG_DOC)), department="engineering", doc_id="eng_guidelines_v2.1"
    )

    store = VectorStore()
    store.delete_document("hr_handbook_v3.2")
    store.delete_document("eng_guidelines_v2.1")

    assert store.add_chunks(hr_chunks) == len(hr_chunks)
    assert store.add_chunks(eng_chunks) == len(eng_chunks)

    results = store.search("vacation policy", top_k=3, department="hr")
    assert len(results) > 0
    assert all(r["metadata"]["department"] == "hr" for r in results)

    engine = RAGEngine()
    response = engine.query("How many vacation days do I get?", department="hr")
    assert response.answer
    assert response.chunks_retrieved > 0
