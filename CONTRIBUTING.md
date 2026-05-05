# Contributing to Enterprise Knowledge Assistant

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start PostgreSQL (via Docker or local install)
docker run -d --name eka-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=knowledge_assistant \
  -p 5432:5432 \
  postgres:16-alpine

# Copy and configure environment
cp ../.env.example ../.env
# Edit ../.env with your API keys

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Code Style

### Python (Backend)
- Use type hints for all function signatures
- Follow PEP 8 naming conventions
- Use `async`/`await` for all I/O operations
- Keep route handlers thin; business logic goes in services or core modules
- Use FastAPI dependency injection for cross-cutting concerns

### TypeScript (Frontend)
- Use strict TypeScript (no `any` unless unavoidable)
- Follow existing Tailwind CSS patterns for styling
- Keep the monolithic App.tsx structure (no component extraction without discussion)

## Commit Convention

Use conventional commits:

```
feat: add user avatar upload
fix: correct department filter in query endpoint
docs: update API endpoint table in README
refactor: extract token validation to helper
test: add integration tests for document upload
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Ensure all tests pass (`cd backend && python -m pytest tests/ -v`)
4. Ensure frontend builds (`cd frontend && npm run build`)
5. Open a PR with a description of what changed and why
6. Wait for CI to pass and request review

## Architecture Decisions

### Adding a New LLM Provider

1. Create a new client class in `backend/app/core/llm_client.py` extending `BaseLLMClient`
2. Implement `generate()` and `agenerate()` methods
3. Add the provider enum value to `LLMProvider` in `backend/app/config.py`
4. Add configuration fields (API key, model name) to `Settings`
5. Update the `get_llm_client()` factory function
6. Add the provider's package to `requirements.txt`
7. Document the new provider in README.md

### Adding a New Document Type

1. Add the extension to `ALLOWED_EXTENSIONS` in `backend/app/api/documents.py`
2. Add a parser method to `DocumentParser` in `backend/app/core/document_processor.py`
3. Update the file type validation in the frontend upload form

## Running Tests

```bash
# All backend tests
cd backend && python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_rag_pipeline.py -v

# Full RAG pipeline (needs LLM API key)
python -m tests.test_rag_pipeline --full

# Frontend
cd frontend && npm run lint && npm run build
```

## Project Layout

See the [README](README.md#project-structure) for the full directory tree and component descriptions.
