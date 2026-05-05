"""
RAG query API routes: ask questions, get answers with citations.

The query pipeline:
  1. Authenticate user and get their department
  2. Apply RBAC department filter to vector search
  3. Run RAG engine (embed → retrieve → generate)
  4. Save query to history
  5. Return answer with sources, confidence, and escalation flag
"""

import json
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserRole, QueryHistory, Department
from app.schemas import (
    QueryRequest, QueryResponse, SourceCitation,
    QueryHistoryItem, QueryHistoryResponse,
)
from app.middleware import get_current_user, require_rate_limit
from app.core.rag_engine import RAGEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["Knowledge Query"])


def _get_rag_engine() -> RAGEngine:
    """Lazy singleton for RAG engine."""
    if not hasattr(_get_rag_engine, "_instance"):
        _get_rag_engine._instance = RAGEngine()
    return _get_rag_engine._instance


@router.post("/", response_model=QueryResponse)
async def ask_question(
    req: QueryRequest,
    _: None = Depends(require_rate_limit(limit=30, window_seconds=60)),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Ask a question to the knowledge base.

    RBAC enforcement:
      - Employees can only search their department's documents
      - Admins can search all departments or filter by specific one
      - Super admins have unrestricted access
    """
    start_time = time.time()

    # Determine department filter based on RBAC
    department = None
    departments = None

    if user.role == UserRole.EMPLOYEE:
        # Employees can ONLY search their department
        if user.department:
            department = user.department.name
        else:
            department = "general"
    elif req.department_filter:
        # Admins can optionally filter by department
        department = req.department_filter
    # else: admins/super_admins see everything (no filter)

    # Run RAG query
    engine = _get_rag_engine()
    try:
        response = await engine.aquery(
            question=req.question,
            department=department,
            departments=departments,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process your question. Please try again.")

    response_time_ms = int((time.time() - start_time) * 1000)

    # Save to query history
    sources_json = json.dumps(response.sources)
    history = QueryHistory(
        user_id=user.id,
        question=req.question,
        answer=response.answer,
        confidence=response.confidence,
        needs_escalation=response.needs_escalation,
        sources=sources_json,
        model_used=response.model_used,
        tokens_used=response.tokens_used,
        chunks_retrieved=response.chunks_retrieved,
        response_time_ms=response_time_ms,
        department_filter=department,
    )
    db.add(history)
    await db.flush()

    return QueryResponse(
        answer=response.answer,
        sources=[
            SourceCitation(
                document=s.get("document", "Unknown"),
                page=s.get("page", "N/A"),
                department=s.get("department", "general"),
                relevance_score=s.get("relevance_score", 0.0),
            )
            for s in response.sources
        ],
        confidence=response.confidence,
        needs_escalation=response.needs_escalation,
        model_used=response.model_used,
        tokens_used=response.tokens_used,
        chunks_retrieved=response.chunks_retrieved,
        response_time_ms=response_time_ms,
        query_id=history.id,
    )


@router.get("/history", response_model=QueryHistoryResponse)
async def get_query_history(
    page: int = QueryParam(1, ge=1),
    page_size: int = QueryParam(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the current user's query history."""
    query = select(QueryHistory).where(QueryHistory.user_id == user.id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.order_by(QueryHistory.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    queries = result.scalars().all()

    return QueryHistoryResponse(
        queries=[
            QueryHistoryItem(
                id=q.id,
                question=q.question,
                answer=q.answer,
                confidence=q.confidence,
                needs_escalation=q.needs_escalation,
                sources=q.sources,
                model_used=q.model_used,
                response_time_ms=q.response_time_ms,
                created_at=q.created_at,
            )
            for q in queries
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
