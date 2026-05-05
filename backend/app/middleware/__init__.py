"""
Auth middleware: JWT validation and RBAC enforcement.

Provides FastAPI dependencies:
  - get_current_user: extracts and validates user from JWT
  - require_admin: ensures user has admin or super_admin role
  - require_super_admin: ensures user has super_admin role
"""

import logging
from typing import Optional
from uuid import UUID
from time import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, UserRole
from app.services.auth_service import decode_token

logger = logging.getLogger(__name__)

# Bearer token extractor
security = HTTPBearer(auto_error=False)
_rate_limit_buckets = defaultdict(deque)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: extract and validate user from JWT bearer token.

    Raises 401 if token is missing, invalid, or user not found.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    # Load user from DB with department info
    result = await db.execute(
        select(User).where(User.id == UUID(user_id)).options(selectinload(User.department))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising for unauthenticated requests."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(*roles: UserRole):
    """
    Factory for role-based access control dependencies.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))])
    """
    async def check_role(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in roles]}",
            )
        return user
    return check_role


# Convenience dependencies
require_admin = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_super_admin = require_role(UserRole.SUPER_ADMIN)


def _check_rate_limit(bucket_key: str, limit: int, window_seconds: int) -> bool:
    """Sliding-window in-memory rate limiter."""
    now = time()
    window_start = now - window_seconds
    bucket = _rate_limit_buckets[bucket_key]

    while bucket and bucket[0] < window_start:
        bucket.popleft()

    if len(bucket) >= limit:
        return False

    bucket.append(now)
    return True


def require_rate_limit(limit: int, window_seconds: int = 60):
    """Dependency factory for per-user/IP rate limiting."""

    async def check_limit(
        request: Request,
        user: Optional[User] = Depends(get_optional_user),
    ):
        client_ip = request.client.host if request.client else "unknown"
        identity = str(user.id) if user else client_ip
        bucket_key = f"{request.url.path}:{identity}"
        allowed = _check_rate_limit(bucket_key, limit=limit, window_seconds=window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {limit} requests per {window_seconds} seconds.",
            )

    return check_limit
