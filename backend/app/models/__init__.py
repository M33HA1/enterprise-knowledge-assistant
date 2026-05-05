"""
SQLAlchemy database models for the Enterprise Knowledge Assistant.

Tables:
  - users: Authentication, roles, departments
  - documents: Uploaded document metadata
  - query_history: User query log with responses
  - departments: Department definitions for RBAC
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, Enum as SAEnum, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    EMPLOYEE = "employee"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class DocumentStatus(str, enum.Enum):
    PROCESSING = "processing"
    ACTIVE = "active"
    FAILED = "failed"
    ARCHIVED = "archived"


# ─── Models ───────────────────────────────────────────────────────────────────

class Department(Base):
    """Department for RBAC-based content visibility."""
    __tablename__ = "departments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="department")
    documents = relationship("Document", back_populates="department")

    def __repr__(self):
        return f"<Department {self.name}>"


class User(Base):
    """User account with role and department assignment."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Null for OAuth-only users
    full_name = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String(500), nullable=True)

    # OAuth fields
    oauth_provider = Column(String(50), nullable=True)  # "google", "microsoft"
    oauth_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    department = relationship("Department", back_populates="users")
    queries = relationship("QueryHistory", back_populates="user", cascade="all, delete-orphan")
    uploaded_documents = relationship("Document", back_populates="uploaded_by_user")

    def __repr__(self):
        return f"<User {self.email} role={self.role}>"


class Document(Base):
    """Metadata for uploaded knowledge base documents."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, docx, txt
    file_size = Column(Integer, nullable=False)  # bytes
    file_path = Column(String(1000), nullable=False)  # local storage path

    # Processing metadata
    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.PROCESSING)
    chunk_count = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # RBAC
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Description / tags for search
    description = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)  # Comma-separated tags

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    department = relationship("Department", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="uploaded_documents")

    # Indexes
    __table_args__ = (
        Index("ix_documents_department_status", "department_id", "status"),
    )

    def __repr__(self):
        return f"<Document {self.filename} status={self.status}>"


class QueryHistory(Base):
    """Log of user queries and RAG responses for history display."""
    __tablename__ = "query_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Query details
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    needs_escalation = Column(Boolean, default=False)

    # RAG metadata
    sources = Column(Text, nullable=True)  # JSON string of source citations
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, default=0)
    chunks_retrieved = Column(Integer, default=0)
    response_time_ms = Column(Integer, nullable=True)

    # Context
    department_filter = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="queries")

    # Indexes
    __table_args__ = (
        Index("ix_query_history_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<QueryHistory user={self.user_id} q={self.question[:50]}>"
