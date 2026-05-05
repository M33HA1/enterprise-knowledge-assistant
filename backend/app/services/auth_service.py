"""
Authentication service: JWT tokens, password hashing, Google OAuth.

Security decisions:
  - bcrypt for password hashing (industry standard, slow = secure)
  - JWT with HS256 (simple, sufficient for single-service apps)
  - Access tokens expire in 60 min, refresh tokens in 7 days
  - OAuth users get a random password hash (can't use password login)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import User, UserRole, Department

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token (longer-lived)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    department_id: Optional[UUID] = None,
    role: UserRole = UserRole.EMPLOYEE,
) -> User:
    """Register a new user with password authentication."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError(f"Email {email} is already registered")

    # Validate department exists if provided
    if department_id:
        dept_result = await db.execute(select(Department).where(Department.id == department_id))
        if not dept_result.scalar_one_or_none():
            raise ValueError(f"Department {department_id} not found")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        department_id=department_id,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user with email + password. Returns None if invalid."""
    result = await db.execute(
        select(User).where(User.email == email).options(selectinload(User.department))
    )
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    return user


async def get_or_create_oauth_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    provider: str,
    oauth_id: str,
    avatar_url: Optional[str] = None,
) -> User:
    """Get or create a user from OAuth login."""
    result = await db.execute(
        select(User).where(User.email == email).options(selectinload(User.department))
    )
    user = result.scalar_one_or_none()

    if user:
        # Update OAuth info and last login
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        user.last_login = datetime.now(timezone.utc)
        if avatar_url:
            user.avatar_url = avatar_url
        return user

    # Create new user
    user = User(
        email=email,
        full_name=full_name,
        oauth_provider=provider,
        oauth_id=oauth_id,
        avatar_url=avatar_url,
        role=UserRole.EMPLOYEE,
        last_login=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    return user


def create_token_pair(user: User) -> dict:
    """Create access + refresh token pair for a user."""
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value if isinstance(user.role, UserRole) else user.role,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
