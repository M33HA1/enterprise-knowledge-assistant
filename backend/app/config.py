"""
Application configuration using Pydantic Settings.

All sensitive values are loaded from environment variables or a .env file.
This is the single source of truth for configuration across the entire app.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"


class Settings(BaseSettings):
    """
    Central configuration for the Enterprise Knowledge Assistant.

    Priority: environment variable > .env file > default value.
    """

    # ─── Application ───────────────────────────────────────────────
    APP_NAME: str = "Enterprise Knowledge Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ─── LLM Configuration ────────────────────────────────────────
    LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"  # Cheapest capable model

    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # Google Gemini (free tier friendly)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # ─── Embedding Configuration ──────────────────────────────────
    EMBEDDING_PROVIDER: EmbeddingProvider = EmbeddingProvider.SENTENCE_TRANSFORMERS
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # Free, local, 384-dim
    EMBEDDING_DIMENSION: int = 384

    # ─── ChromaDB Configuration ───────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"

    # ─── Document Processing ──────────────────────────────────────
    CHUNK_SIZE: int = 500        # Characters per chunk
    CHUNK_OVERLAP: int = 50      # Overlap between chunks
    MAX_FILE_SIZE_MB: int = 50   # Max upload size
    UPLOAD_DIR: str = "./data/uploads"

    # ─── RAG Configuration ────────────────────────────────────────
    TOP_K_RESULTS: int = 5               # Number of chunks to retrieve
    CONFIDENCE_THRESHOLD: float = 0.3    # Below this → flag for human review
    MAX_CONTEXT_LENGTH: int = 4000       # Max chars of context sent to LLM

    # ─── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_assistant"

    # ─── Authentication ───────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # ─── CORS ─────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance
settings = Settings()
