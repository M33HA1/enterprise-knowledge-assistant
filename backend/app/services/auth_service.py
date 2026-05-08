"""
Authentication service: JWT tokens, password hashing, Google OAuth.

Security decisions:
  - bcrypt directly for password hashing (passlib removed — unmaintained)
  - JWT with HS256 (simple, sufficient for single-service apps)
  - Access tokens expire in 60 min, refresh tokens in 7 days
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import User, UserRole, Department

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
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
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ValueError(f"Email {email} is already registered")

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

    if not user:
        return None
    if not user.hashed_password:
        # OAuth-only account — cannot use password login
        raise ValueError("This account uses Google sign-in. Please use the 'Continue with Google' button.")
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None

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
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        user.last_login = datetime.now(timezone.utc)
        if avatar_url:
            user.avatar_url = avatar_url
        return user

    # Create new user — first OAuth user gets super_admin, rest get employee
    from sqlalchemy import func
    user_count_result = await db.execute(select(func.count()).select_from(User).where(User.oauth_provider.isnot(None)))
    user_count = user_count_result.scalar()
    role = UserRole.SUPER_ADMIN if user_count == 0 else UserRole.EMPLOYEE

    user = User(
        email=email,
        full_name=full_name,
        oauth_provider=provider,
        oauth_id=oauth_id,
        avatar_url=avatar_url,
        role=role,
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
