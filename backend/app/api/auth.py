"""
Authentication API routes: register, login, token refresh, Google OAuth.
"""

import logging
from time import time
from uuid import uuid4
import base64
import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.database import get_db
from app.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest,
    UserResponse, OAuthExchangeRequest,
)
from app.services.auth_service import (
    register_user, authenticate_user, create_token_pair,
    decode_token, get_or_create_oauth_user,
)
from app.middleware import get_current_user, require_rate_limit
from app.models import User, UserRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
_oauth_exchange_store: dict[str, tuple[dict, float]] = {}
_oauth_pkce_store: dict[str, tuple[str, float]] = {}
_OAUTH_EXCHANGE_TTL_SECONDS = 60
_OAUTH_STATE_TTL_SECONDS = 600


def _put_oauth_exchange(tokens: dict) -> str:
    code = uuid4().hex
    _oauth_exchange_store[code] = (tokens, time() + _OAUTH_EXCHANGE_TTL_SECONDS)
    return code


def _pop_oauth_exchange(code: str) -> dict | None:
    item = _oauth_exchange_store.pop(code, None)
    if not item:
        return None
    tokens, expires_at = item
    if time() > expires_at:
        return None
    return tokens


def _create_oauth_state(state_id: str) -> str:
    """Create a short-lived signed OAuth state token for CSRF protection."""
    from app.config import settings

    now = int(time())
    payload = {
        "sid": state_id,
        "nonce": uuid4().hex,
        "type": "oauth_state",
        "iat": now,
        "exp": now + _OAUTH_STATE_TTL_SECONDS,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _validate_oauth_state(state: str) -> dict | None:
    """Validate OAuth state token signature + expiry and return payload."""
    from app.config import settings

    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "oauth_state":
            return None
        return payload
    except JWTError:
        return None


def _create_pkce_pair() -> tuple[str, str]:
    """
    Create PKCE code verifier/challenge pair (S256).
    verifier: high-entropy random string
    challenge: base64url(sha256(verifier))
    """
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")
    return code_verifier, code_challenge


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    try:
        user = await register_user(
            db=db,
            email=req.email,
            password=req.password,
            full_name=req.full_name,
            department_id=req.department_id,
        )
        tokens = create_token_pair(user)
        return TokenResponse(
            **tokens,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                department_id=user.department_id,
                is_active=user.is_active,
                created_at=user.created_at,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    _: None = Depends(require_rate_limit(limit=10, window_seconds=60)),
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    try:
        user = await authenticate_user(db, req.email, req.password)
    except ValueError as e:
        # OAuth-only account trying to use password login
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    tokens = create_token_pair(user)
    dept_name = user.department.name if user.department else None
    return TokenResponse(
        **tokens,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            department_id=user.department_id,
            department_name=dept_name,
            is_active=user.is_active,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
        ),
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an expired access token using a valid refresh token."""
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    from sqlalchemy import select
    from uuid import UUID
    result = await db.execute(select(User).where(User.id == UUID(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    tokens = create_token_pair(user)
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    dept_name = user.department.name if user.department else None
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department_id=user.department_id,
        department_name=dept_name,
        is_active=user.is_active,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


@router.get("/google/login")
async def google_login_redirect():
    """Returns the Google OAuth URL for the frontend to redirect to."""
    from app.config import settings
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    state_id = uuid4().hex
    code_verifier, code_challenge = _create_pkce_pair()
    _oauth_pkce_store[state_id] = (code_verifier, time() + _OAUTH_STATE_TTL_SECONDS)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": _create_oauth_state(state_id),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    import urllib.parse
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {"auth_url": url}


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback. Exchange code for tokens, create/get user."""
    from app.config import settings
    import httpx
    import urllib.parse

    state_payload = _validate_oauth_state(state)
    if not state_payload:
        error_params = urllib.parse.urlencode({"error": "Invalid or expired OAuth state"})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?{error_params}", status_code=302)
    state_id = state_payload.get("sid")
    pkce_item = _oauth_pkce_store.pop(state_id, None) if state_id else None
    if not pkce_item:
        error_params = urllib.parse.urlencode({"error": "Missing or expired PKCE verifier"})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?{error_params}", status_code=302)
    code_verifier, verifier_expires = pkce_item
    if time() > verifier_expires:
        error_params = urllib.parse.urlencode({"error": "Expired PKCE verifier"})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?{error_params}", status_code=302)

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange OAuth code")
        token_data = token_resp.json()

        # Get user info
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        userinfo = userinfo_resp.json()

    # Create or get user
    user = await get_or_create_oauth_user(
        db=db,
        email=userinfo["email"],
        full_name=userinfo.get("name", userinfo["email"]),
        provider="google",
        oauth_id=userinfo["id"],
        avatar_url=userinfo.get("picture"),
    )

    tokens = create_token_pair(user)
    exchange_code = _put_oauth_exchange(tokens)
    params = urllib.parse.urlencode(
        {
            "oauth_code": exchange_code,
            "oauth": "google",
        }
    )
    frontend_redirect = f"{settings.FRONTEND_URL}/?{params}"
    return RedirectResponse(url=frontend_redirect, status_code=302)


@router.post("/oauth/exchange", response_model=dict)
async def exchange_oauth_code(req: OAuthExchangeRequest):
    """Exchange a short-lived one-time OAuth code for token pair."""
    tokens = _pop_oauth_exchange(req.oauth_code)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth exchange code",
        )
    return tokens
