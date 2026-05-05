"""
Admin API routes: user management, department management, system stats.

All routes require admin or super_admin role.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, UserRole, Department, Document, DocumentStatus, QueryHistory
from app.schemas import (
    UserResponse, UserUpdate, DepartmentCreate, DepartmentResponse,
    MessageResponse,
)
from app.middleware import get_current_user, require_admin, require_super_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# ─── Department Management ───────────────────────────────────────────────────

@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    req: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Create a new department."""
    # Check uniqueness
    existing = await db.execute(select(Department).where(Department.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Department '{req.name}' already exists")

    dept = Department(name=req.name, description=req.description)
    db.add(dept)
    await db.flush()
    return DepartmentResponse(id=dept.id, name=dept.name, description=dept.description, created_at=dept.created_at)


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all departments with user/doc counts."""
    result = await db.execute(select(Department).order_by(Department.name))
    depts = result.scalars().all()

    response = []
    for dept in depts:
        user_count = await db.execute(select(func.count()).where(User.department_id == dept.id))
        doc_count = await db.execute(select(func.count()).where(Document.department_id == dept.id))
        response.append(DepartmentResponse(
            id=dept.id,
            name=dept.name,
            description=dept.description,
            created_at=dept.created_at,
            user_count=user_count.scalar(),
            document_count=doc_count.scalar(),
        ))
    return response


@router.delete("/departments/{dept_id}", response_model=MessageResponse)
async def delete_department(
    dept_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_super_admin),
):
    """Delete a department. Super admin only."""
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    # Unassign users and docs from this department
    await db.execute(update(User).where(User.department_id == dept_id).values(department_id=None))
    await db.execute(update(Document).where(Document.department_id == dept_id).values(department_id=None))
    await db.delete(dept)
    return MessageResponse(message=f"Department '{dept.name}' deleted")


# ─── User Management ─────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    role: Optional[str] = Query(None),
    department_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """List all users. Admin only."""
    query = select(User).options(selectinload(User.department))
    if role:
        try:
            query = query.where(User.role == UserRole(role))
        except ValueError:
            pass
    if department_id:
        query = query.where(User.department_id == department_id)

    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return [
        UserResponse(
            id=u.id, email=u.email, full_name=u.full_name,
            role=u.role, department_id=u.department_id,
            department_name=u.department.name if u.department else None,
            is_active=u.is_active, avatar_url=u.avatar_url, created_at=u.created_at,
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    req: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update a user's role, department, or status. Admin only."""
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.department))
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent non-super-admins from creating super_admins
    if req.role == UserRole.SUPER_ADMIN and admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admins can promote to super admin")

    if req.full_name is not None:
        target_user.full_name = req.full_name
    if req.role is not None:
        target_user.role = req.role
    if req.department_id is not None:
        target_user.department_id = req.department_id
    if req.is_active is not None:
        target_user.is_active = req.is_active

    await db.flush()
    # Reload department relation
    await db.refresh(target_user, ["department"])

    return UserResponse(
        id=target_user.id, email=target_user.email, full_name=target_user.full_name,
        role=target_user.role, department_id=target_user.department_id,
        department_name=target_user.department.name if target_user.department else None,
        is_active=target_user.is_active, avatar_url=target_user.avatar_url,
        created_at=target_user.created_at,
    )


# ─── System Stats ────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Get system-wide statistics. Admin only."""
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar()
    doc_count = (await db.execute(
        select(func.count()).select_from(Document).where(Document.status == DocumentStatus.ACTIVE)
    )).scalar()
    query_count = (await db.execute(select(func.count()).select_from(QueryHistory))).scalar()
    dept_count = (await db.execute(select(func.count()).select_from(Department))).scalar()

    # Average confidence
    avg_conf = (await db.execute(
        select(func.avg(QueryHistory.confidence)).where(QueryHistory.confidence.isnot(None))
    )).scalar()

    # Escalation rate
    escalated = (await db.execute(
        select(func.count()).select_from(QueryHistory).where(QueryHistory.needs_escalation == True)
    )).scalar()

    from app.core.rag_engine import RAGEngine
    try:
        engine = RAGEngine()
        total_chunks = engine.total_chunks
    except Exception:
        total_chunks = 0

    return {
        "total_users": user_count,
        "total_documents": doc_count,
        "total_queries": query_count,
        "total_departments": dept_count,
        "total_chunks": total_chunks,
        "avg_confidence": round(avg_conf, 3) if avg_conf else None,
        "escalation_rate": round(escalated / max(query_count, 1), 3),
        "query_resolution_rate": round(1 - (escalated / max(query_count, 1)), 3),
    }
