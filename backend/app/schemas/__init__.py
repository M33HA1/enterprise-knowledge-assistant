"""
Pydantic schemas for API request/response validation.

Organized by domain: auth, users, documents, queries.
"""

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRoleSchema(str, Enum):
    EMPLOYEE = "employee"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class DocumentStatusSchema(str, Enum):
    PROCESSING = "processing"
    ACTIVE = "active"
    FAILED = "failed"
    ARCHIVED = "archived"


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    department_id: Optional[UUID] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class OAuthExchangeRequest(BaseModel):
    oauth_code: str = Field(min_length=12, max_length=255)


# ─── User Schemas ─────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRoleSchema
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRoleSchema] = None
    department_id: Optional[UUID] = None
    is_active: Optional[bool] = None


# ─── Department Schemas ───────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    user_count: Optional[int] = None
    document_count: Optional[int] = None

    model_config = {"from_attributes": True}


# ─── Document Schemas ─────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: UUID
    title: str
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatusSchema
    chunk_count: int
    total_pages: int
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    uploaded_by: Optional[UUID] = None
    uploader_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


# ─── Query Schemas ────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    department_filter: Optional[str] = None  # Override RBAC for admins


class SourceCitation(BaseModel):
    document: str
    page: Any
    department: str
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    confidence: float
    needs_escalation: bool
    model_used: str
    tokens_used: int
    chunks_retrieved: int
    response_time_ms: int
    query_id: UUID


class QueryHistoryItem(BaseModel):
    id: UUID
    question: str
    answer: str
    confidence: Optional[float] = None
    needs_escalation: bool
    sources: Optional[str] = None
    model_used: Optional[str] = None
    response_time_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QueryHistoryResponse(BaseModel):
    queries: List[QueryHistoryItem]
    total: int
    page: int
    page_size: int


# ─── General ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    vector_store: str
    llm_provider: str


# Fix forward reference
TokenResponse.model_rebuild()
