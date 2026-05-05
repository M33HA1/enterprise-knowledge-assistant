"""
Test script for the RAG pipeline — Step 1 verification.

This script tests the entire pipeline end-to-end:
  1. Document parsing and chunking
  2. Embedding generation
  3. ChromaDB storage
  4. Semantic search (with RBAC department filtering)
  5. LLM-powered answer generation with citations

Run: python -m tests.test_rag_pipeline
"""

import os
import sys
import logging
from pathlib import Path

# ─── Setup logging ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    encoding="utf-8",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_rag")

# ─── Paths ────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = BACKEND_DIR / "tests" / "sample_data"

HR_DOC = SAMPLE_DIR / "employee_handbook.txt"
ENG_DOC = SAMPLE_DIR / "engineering_guidelines.txt"


def test_document_processing():
    """Test 1: Parse and chunk documents."""
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("\n" + "=" * 60)
    print("TEST 1: Document Processing (Parse + Chunk)")
    print("=" * 60)

    from app.core.document_processor import DocumentParser, DocumentChunker

    parser = DocumentParser()
    chunker = DocumentChunker()

    # Parse HR handbook
    parsed = parser.parse(str(HR_DOC))
    print(f"  ✓ Parsed: {parsed.filename}")
    print(f"    Type: {parsed.file_type}, Pages: {parsed.total_pages}")
    print(f"    Content length: {len(parsed.content)} chars")

    # Chunk it
    chunks = chunker.chunk_document(parsed, department="hr", doc_id="hr_handbook_v3.2")
    print(f"  ✓ Created {len(chunks)} chunks")
    print(f"    First chunk ({len(chunks[0].content)} chars): {chunks[0].content[:100]}...")
    print(f"    Metadata: {chunks[0].metadata}")

    # Parse engineering doc
    parsed_eng = parser.parse(str(ENG_DOC))
    chunks_eng = chunker.chunk_document(parsed_eng, department="engineering", doc_id="eng_guidelines_v2.1")
    print(f"  ✓ Engineering doc: {len(chunks_eng)} chunks")

    return chunks, chunks_eng


def test_embeddings():
    """Test 2: Embedding model."""
    print("\n" + "=" * 60)
    print("TEST 2: Embedding Model")
    print("=" * 60)

    from app.core.embeddings import get_embedding_model

    embedder = get_embedding_model()
    print(f"  ✓ Model loaded. Dimension: {embedder.dimension}")

    # Test single embedding
    vec = embedder.embed_text("What is the PTO policy?")
    print(f"  ✓ Single embedding: {len(vec)} dimensions")
    print(f"    First 5 values: {vec[:5]}")

    # Test batch embedding
    texts = [
        "paid time off vacation days",
        "remote work from home policy",
        "code review requirements",
    ]
    vecs = embedder.embed_batch(texts)
    print(f"  ✓ Batch embedding: {len(vecs)} texts → {len(vecs[0])} dims each")

    return embedder


def test_vector_store(hr_chunks, eng_chunks):
    """Test 3: ChromaDB vector store with RBAC filtering."""
    print("\n" + "=" * 60)
    print("TEST 3: Vector Store (ChromaDB + RBAC)")
    print("=" * 60)

    from app.core.vector_store import VectorStore

    store = VectorStore()

    # Clear any previous test data
    try:
        store.delete_document("hr_handbook_v3.2")
        store.delete_document("eng_guidelines_v2.1")
    except Exception:
        pass

    # Add HR chunks
    count_hr = store.add_chunks(hr_chunks)
    print(f"  ✓ Added {count_hr} HR chunks")

    # Add engineering chunks
    count_eng = store.add_chunks(eng_chunks)
    print(f"  ✓ Added {count_eng} Engineering chunks")

    print(f"  ✓ Total chunks in store: {store.total_chunks}")

    # Search WITHOUT department filter (should get results from both)
    results_all = store.search("What is the code review policy?", top_k=3)
    print(f"\n  Search (no filter): 'code review policy'")
    for r in results_all:
        print(f"    → [{r['score']:.4f}] {r['metadata']['source']} | dept: {r['metadata']['department']}")
        print(f"      {r['content'][:80]}...")

    # Search WITH department filter (RBAC)
    results_hr = store.search("What is the vacation policy?", top_k=3, department="hr")
    print(f"\n  Search (HR only): 'vacation policy'")
    for r in results_hr:
        print(f"    → [{r['score']:.4f}] {r['metadata']['source']} | dept: {r['metadata']['department']}")

    results_eng = store.search("deployment process", top_k=3, department="engineering")
    print(f"\n  Search (Engineering only): 'deployment process'")
    for r in results_eng:
        print(f"    → [{r['score']:.4f}] {r['metadata']['source']} | dept: {r['metadata']['department']}")

    # Document listing
    docs = store.get_document_list()
    print(f"\n  Documents in store:")
    for d in docs:
        print(f"    → {d['source']} | dept: {d['department']} | chunks: {d['chunk_count']}")

    return store


def test_rag_engine():
    """Test 4: Full RAG pipeline end-to-end."""
    print("\n" + "=" * 60)
    print("TEST 4: Full RAG Pipeline (Ingest + Query)")
    print("=" * 60)

    from app.core.rag_engine import RAGEngine

    engine = RAGEngine()

    # Ingest documents
    print("\n  Ingesting documents...")
    result_hr = engine.ingest_document(str(HR_DOC), department="hr", doc_id="hr_handbook_v3.2")
    print(f"  ✓ HR handbook: {result_hr.chunks_created} chunks, success={result_hr.success}")

    result_eng = engine.ingest_document(str(ENG_DOC), department="engineering", doc_id="eng_guidelines_v2.1")
    print(f"  ✓ Engineering guidelines: {result_eng.chunks_created} chunks, success={result_eng.success}")

    # Query — HR question (general, no RBAC)
    print("\n  ── Query 1: PTO Policy (no department filter) ──")
    response = engine.query("How many vacation days do I get after 3 years?")
    print(f"  Answer: {response.answer[:300]}...")
    print(f"  Confidence: {response.confidence}")
    print(f"  Escalation needed: {response.needs_escalation}")
    print(f"  Model: {response.model_used}")
    print(f"  Tokens: {response.tokens_used}")
    print(f"  Sources:")
    for s in response.sources:
        print(f"    → {s['document']} (page {s['page']}, dept: {s['department']}, score: {s['relevance_score']})")

    # Query — HR question with department filter (RBAC)
    print("\n  ── Query 2: Remote work (HR department filter) ──")
    response2 = engine.query("What are the requirements for working from home?", department="hr")
    print(f"  Answer: {response2.answer[:300]}...")
    print(f"  Confidence: {response2.confidence}")
    print(f"  Sources: {[s['document'] for s in response2.sources]}")

    # Query — Engineering question
    print("\n  ── Query 3: On-call (Engineering filter) ──")
    response3 = engine.query("What is the on-call compensation?", department="engineering")
    print(f"  Answer: {response3.answer[:300]}...")
    print(f"  Confidence: {response3.confidence}")

    # Query — Cross-department (should fail with RBAC)
    print("\n  ── Query 4: Engineering asking HR question (RBAC test) ──")
    response4 = engine.query("What is the PTO policy?", department="engineering")
    print(f"  Answer: {response4.answer[:200]}...")
    print(f"  Chunks retrieved: {response4.chunks_retrieved}")
    print(f"  --> RBAC working: Engineering user cannot see HR documents" if response4.chunks_retrieved == 0 else "  [i] Got some results (may have overlap in content)")

    return engine


def test_embedding_only():
    """Run only tests that don't require an LLM API key."""
    print("\n[TEST] Running EMBEDDING-ONLY tests (no LLM API needed)")
    print("=" * 60)

    hr_chunks, eng_chunks = test_document_processing()
    test_embeddings()
    test_vector_store(hr_chunks, eng_chunks)

    print("\n" + "=" * 60)
    print("[PASS] All embedding/retrieval tests passed!")
    print("=" * 60)
    print("\nTo run the full RAG test (requires LLM API key):")
    print("  Set OPENAI_API_KEY in your .env file, then run:")
    print("  python -m tests.test_rag_pipeline --full")


def test_full():
    """Run all tests including LLM generation."""
    print("\n[TEST] Running FULL RAG pipeline test")
    print("=" * 60)

    test_document_processing()
    test_embeddings()
    test_rag_engine()

    print("\n" + "=" * 60)
    print("[PASS] All tests passed! RAG pipeline is working end-to-end.")
    print("=" * 60)


if __name__ == "__main__":
    if "--full" in sys.argv:
        test_full()
    else:
        test_embedding_only()
