"""
Application configuration using Pydantic Settings.

All sensitive values are loaded from environment variables or a .env file.
This is the single source of truth for configuration across the entire app.
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    GROK = "grok"


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"


class Settings(BaseSettings):
    """
    Central configuration for the Enterprise Knowledge Assistant.

    Priority: environment variable > .env file > default value.
    """

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ─── Application ───────────────────────────────────────────────
    APP_NAME: str = "Enterprise Knowledge Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ─── LLM Configuration ────────────────────────────────────────
    LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"

    # Google Gemini (free tier friendly)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Grok (xAI)
    GROK_API_KEY: Optional[str] = None
    GROK_MODEL: str = "grok-2-latest"

    # ─── Embedding Configuration ──────────────────────────────────
    EMBEDDING_PROVIDER: EmbeddingProvider = EmbeddingProvider.SENTENCE_TRANSFORMERS
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ─── ChromaDB Configuration ───────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"

    # ─── Document Processing ──────────────────────────────────────
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    MAX_FILE_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./data/uploads"

    # ─── RAG Configuration ────────────────────────────────────────
    TOP_K_RESULTS: int = 5
    CONFIDENCE_THRESHOLD: float = 0.3
    MAX_CONTEXT_LENGTH: int = 4000

    # ─── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_assistant"

    # ─── Authentication ───────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480   # 8 hours — full workday session
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30      # 30 days — stay logged in

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # ─── CORS ─────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"


# Singleton settings instance
settings = Settings()
