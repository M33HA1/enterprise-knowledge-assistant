"""
Enterprise Knowledge Assistant — FastAPI Application Entry Point.

This is the main application file that:
  1. Creates the FastAPI app with CORS middleware
  2. Registers all API routers
  3. Handles startup/shutdown lifecycle (DB init, seed data)
  4. Provides a health check endpoint
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def validate_config():
    """Warn at startup if placeholder credentials are detected."""
    _PLACEHOLDER_SECRET = "change-this-in-production-use-openssl-rand-hex-32"
    _PLACEHOLDER_OAUTH = "your-google-client-secret"

    if settings.SECRET_KEY == _PLACEHOLDER_SECRET:
        logger.warning(
            "WARNING: SECRET_KEY is set to the default placeholder value. "
            "JWT tokens are insecure. Generate a real key with: "
            "python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    if not settings.GOOGLE_CLIENT_SECRET or settings.GOOGLE_CLIENT_SECRET == _PLACEHOLDER_OAUTH:
        logger.warning(
            "WARNING: GOOGLE_CLIENT_SECRET is not configured or is set to a placeholder value. "
            "Google OAuth will not function until a real secret is provided."
        )


async def seed_default_data():
    """Create default departments and super_admin on first run."""
    from app.database import async_session_factory
    from app.models import Department, User, UserRole
    from app.services.auth_service import hash_password
    from sqlalchemy import select

    async with async_session_factory() as db:
        # Check if departments exist
        result = await db.execute(select(Department).limit(1))
        if result.scalar_one_or_none():
            return  # Already seeded

        logger.info("Seeding default departments and super admin...")

        # Create default departments
        departments = ["General", "HR", "Engineering", "Finance", "Legal", "IT", "Marketing"]
        dept_objects = {}
        for name in departments:
            dept = Department(name=name.lower(), description=f"{name} department")
            db.add(dept)
            dept_objects[name.lower()] = dept

        await db.flush()

        # Create default super admin
        admin = User(
            email="admin@enterprise.com",
            hashed_password=hash_password("admin123"),
            full_name="System Administrator",
            role=UserRole.SUPER_ADMIN,
            department_id=dept_objects["general"].id,
            is_active=True,
        )
        db.add(admin)

        # Create a test employee for each department
        test_users = [
            ("hr_user@enterprise.com", "HR Employee", "hr"),
            ("eng_user@enterprise.com", "Engineering Employee", "engineering"),
            ("finance_user@enterprise.com", "Finance Employee", "finance"),
        ]
        for email, name, dept in test_users:
            user = User(
                email=email,
                hashed_password=hash_password("password123"),
                full_name=name,
                role=UserRole.EMPLOYEE,
                department_id=dept_objects[dept].id,
                is_active=True,
            )
            db.add(user)

        await db.commit()
        logger.info("Seed data created: 7 departments, 1 admin, 3 test employees")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifecycle: startup and shutdown handlers."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    validate_config()
    await init_db()
    await seed_default_data()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info("Database initialized, seed data ready")
    yield
    # Shutdown
    await close_db()
    logger.info("Application shutdown complete")


# ─── Create App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered internal assistant using RAG for policy-aware employee questions",
    lifespan=lifespan,
)

# ─── CORS Middleware ──────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ────────────────────────────────────────────────────────

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.query import router as query_router
from app.api.admin import router as admin_router

app.include_router(auth_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check with component status."""
    from app.schemas import HealthResponse

    # Check database
    db_status = "connected"
    try:
        from app.database import async_session_factory
        from sqlalchemy import text
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    # Check vector store
    vs_status = "unknown"
    try:
        from app.core.vector_store import VectorStore
        vs = VectorStore()
        vs_status = f"connected ({vs.total_chunks} chunks)"
    except Exception:
        vs_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.APP_VERSION,
        database=db_status,
        vector_store=vs_status,
        llm_provider=settings.LLM_PROVIDER.value,
    )
