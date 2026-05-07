# Use a stable Python base image for the backend service
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/data/hf_cache \
    TRANSFORMERS_CACHE=/app/data/hf_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/data/hf_cache

# Install system dependencies needed by the Python stack
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Install Python dependencies first to leverage Docker cache
COPY backend/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r /app/requirements.txt

# Copy backend source code
COPY backend/app /app/app

# Copy Alembic configuration and migrations
COPY backend/alembic.ini /app/alembic.ini
COPY backend/alembic /app/alembic

# Create persistent storage folders for uploads, ChromaDB, and HuggingFace model cache
RUN mkdir -p /app/data/uploads /app/data/chroma_db /app/data/hf_cache && \
    chown -R app:app /app/data

# Pre-download the embedding model so it's baked into the image
# This avoids permission errors and slow first-request downloads at runtime
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" && \
    chown -R app:app /app/data/hf_cache

# Switch to non-root user
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
