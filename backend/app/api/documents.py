"""
Document management API routes: upload, list, delete, download.

Handles the full ingestion pipeline: upload → parse → chunk → embed → store.
Department-based RBAC ensures users only see their department's documents.
"""

import os
import uuid
import logging
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models import User, UserRole, Document, DocumentStatus, Department
from app.schemas import DocumentResponse, DocumentListResponse, MessageResponse
from app.middleware import get_current_user, require_admin, require_rate_limit
from app.core.rag_engine import RAGEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _get_rag_engine() -> RAGEngine:
    """Lazy singleton for RAG engine."""
    if not hasattr(_get_rag_engine, "_instance"):
        _get_rag_engine._instance = RAGEngine()
    return _get_rag_engine._instance


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    department_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    _: None = Depends(require_rate_limit(limit=20, window_seconds=60)),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Upload and ingest a document into the knowledge base.

    Only admins and super_admins can upload documents.
    The document is parsed, chunked, embedded, and stored in ChromaDB.
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Validate file size
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Resolve department
    dept_uuid = None
    dept_name = "general"
    if department_id:
        try:
            dept_uuid = uuid.UUID(department_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid department_id format")
        dept_result = await db.execute(select(Department).where(Department.id == dept_uuid))
        dept = dept_result.scalar_one_or_none()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        dept_name = dept.name

    # Save file to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    doc_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}{ext}")
    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    doc = Document(
        id=uuid.UUID(doc_id),
        title=title,
        filename=file.filename,
        file_type=ext.lstrip("."),
        file_size=file_size,
        file_path=file_path,
        status=DocumentStatus.PROCESSING,
        department_id=dept_uuid,
        uploaded_by=user.id,
        description=description,
        tags=tags,
    )
    db.add(doc)
    await db.flush()

    # Run ingestion pipeline
    try:
        engine = _get_rag_engine()
        result = engine.ingest_document(
            file_path=file_path,
            department=dept_name,
            doc_id=doc_id,
        )
        if result.success:
            doc.status = DocumentStatus.ACTIVE
            doc.chunk_count = result.chunks_created
            # Try to get page count from the parser
            from app.core.document_processor import DocumentParser
            try:
                parsed = DocumentParser.parse(file_path)
                doc.total_pages = parsed.total_pages
            except Exception:
                doc.total_pages = 0
        else:
            doc.status = DocumentStatus.FAILED
            doc.error_message = result.error
    except Exception as e:
        logger.error(f"Ingestion failed for {file.filename}: {e}")
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)

    await db.commit()
    await db.refresh(doc)

    # Load relationships for the response if possible, though we don't strictly need them
    # because they're optional in DocumentResponse.
    dept_name = None
    if doc.department_id:
        dept = await db.get(Department, doc.department_id)
        if dept: dept_name = dept.name
        
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        chunk_count=doc.chunk_count,
        total_pages=doc.total_pages,
        department_id=doc.department_id,
        department_name=dept_name,
        uploaded_by=doc.uploaded_by,
        uploader_name=user.full_name,
        description=doc.description,
        tags=doc.tags,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List documents visible to the current user.

    RBAC: Employees see only their department's docs.
    Admins/super_admins can see all or filter by department.
    """
    query = select(Document).options(selectinload(Document.department), selectinload(Document.uploaded_by_user))

    # RBAC filtering
    if user.role == UserRole.EMPLOYEE and user.department_id:
        query = query.where(Document.department_id == user.department_id)
    elif department_id:
        try:
            query = query.where(Document.department_id == uuid.UUID(department_id))
        except ValueError:
            pass

    # Status filter
    if status_filter:
        try:
            query = query.where(Document.status == DocumentStatus(status_filter))
        except ValueError:
            pass

    # Search by title/filename
    if search:
        query = query.where(
            (Document.title.ilike(f"%{search}%")) | (Document.filename.ilike(f"%{search}%"))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=d.id,
                title=d.title,
                filename=d.filename,
                file_type=d.file_type,
                file_size=d.file_size,
                status=d.status,
                chunk_count=d.chunk_count,
                total_pages=d.total_pages,
                department_id=d.department_id,
                department_name=d.department.name if d.department else None,
                uploaded_by=d.uploaded_by,
                uploader_name=d.uploaded_by_user.full_name if d.uploaded_by_user else None,
                description=d.description,
                tags=d.tags,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in docs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single document by ID."""
    result = await db.execute(
        select(Document)
        .where(Document.id == doc_id)
        .options(selectinload(Document.department), selectinload(Document.uploaded_by_user))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # RBAC check
    if user.role == UserRole.EMPLOYEE and user.department_id and doc.department_id != user.department_id:
        raise HTTPException(status_code=403, detail="You don't have access to this document")

    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        chunk_count=doc.chunk_count,
        total_pages=doc.total_pages,
        department_id=doc.department_id,
        department_name=doc.department.name if doc.department else None,
        uploaded_by=doc.uploaded_by,
        uploader_name=doc.uploaded_by_user.full_name if doc.uploaded_by_user else None,
        description=doc.description,
        tags=doc.tags,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/{doc_id}", response_model=MessageResponse)
async def delete_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Delete a document and its vector embeddings. Admin only."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from vector store
    try:
        engine = _get_rag_engine()
        engine.delete_document(str(doc_id))
    except Exception as e:
        logger.warning(f"Failed to delete vectors for {doc_id}: {e}")

    # Delete file from disk
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception as e:
        logger.warning(f"Failed to delete file {doc.file_path}: {e}")

    # Delete from database
    await db.delete(doc)

    return MessageResponse(message=f"Document '{doc.title}' deleted successfully")
