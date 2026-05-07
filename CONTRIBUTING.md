# Contributing to EKA

Thanks for wanting to improve this. Here's everything you need to get a dev environment running and submit a clean PR.

---

## 🏃 Local dev setup

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Start a local PostgreSQL (Docker is easiest)
docker run -d --name eka-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=knowledge_assistant \
  -p 5432:5432 \
  postgres:16-alpine

# Configure environment
cp ../.env.example ../.env
# Edit ../.env — set LLM_PROVIDER + API key + SECRET_KEY

# Run the server (auto-reloads on file changes)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend at `http://localhost:5173`, backend at `http://localhost:8000`.

---

## 🧪 Running tests

```bash
# All backend tests
cd backend
python -m pytest tests/ -v --tb=short

# Just the config/env tests (fast, no model download)
python -m pytest tests/test_env_config_fix.py tests/test_rate_limit.py -v

# Full RAG pipeline (requires LLM API key in .env)
python -m pytest tests/test_rag_pipeline.py -v

# Frontend
cd frontend
npm run lint
npm run build
```

CI runs all of these automatically on every push to `main`.

---

## 📐 Code style

### Python
- Type hints on all function signatures
- `async`/`await` for all I/O (database, HTTP, file)
- Route handlers stay thin — business logic goes in `services/` or `core/`
- Use FastAPI `Depends()` for auth, DB sessions, and rate limiting
- No `passlib` — use `bcrypt` directly (see `auth_service.py`)

### TypeScript
- No `any` — use `unknown` + type narrowing or define an interface
- All API error handling via the `apiErrMsg()` helper in `App.tsx`
- Tailwind only — no inline styles, no CSS modules
- Keep components in `App.tsx` unless they're genuinely reusable

---

## 📝 Commit convention

Use [conventional commits](https://www.conventionalcommits.org/):

```
feat: add document tagging support
fix: resolve bcrypt compatibility with Python 3.12
docs: add API curl examples to README
refactor: extract confidence scoring to helper function
test: add property tests for rate limiter
chore: upgrade sentence-transformers to 3.4.1
```

---

## 🔀 PR process

1. Branch from `main`: `git checkout -b feat/your-feature`
2. Make changes with clear commits
3. Run tests locally before pushing
4. Open a PR — describe what changed and why
5. CI must be green (backend tests + frontend lint/build + Docker build)
6. One approval required to merge

---

## 🧩 Common extension patterns

### Adding a new LLM provider

```python
# 1. backend/app/config.py — add to enum
class LLMProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    MYMODEL = "mymodel"   # ← add here

# 2. Add config fields
class Settings(BaseSettings):
    MYMODEL_API_KEY: Optional[str] = None
    MYMODEL_MODEL: str = "my-model-name"

# 3. backend/app/core/llm_client.py — new class
class MyModelClient(BaseLLMClient):
    def __init__(self):
        ...
    def generate(self, query, context, system_prompt=None) -> LLMResponse:
        ...
    async def agenerate(self, query, context, system_prompt=None) -> LLMResponse:
        ...

# 4. Update factory
def get_llm_client() -> BaseLLMClient:
    if settings.LLM_PROVIDER == LLMProvider.MYMODEL:
        return MyModelClient()
    ...
```

### Adding a new document type

```python
# backend/app/api/documents.py
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}  # add here

# backend/app/core/document_processor.py
class DocumentParser:
    @staticmethod
    def parse(file_path: str) -> ParsedDocument:
        ...
        elif ext == ".md":
            return DocumentParser._parse_md(path)   # add branch

    @staticmethod
    def _parse_md(path: Path) -> ParsedDocument:
        content = path.read_text(encoding="utf-8")
        return ParsedDocument(
            filename=path.name,
            content=content,
            pages=[content],
            file_type="md",
            total_pages=1,
        )
```

```tsx
// frontend/src/App.tsx — update file input
<input type="file" accept=".pdf,.docx,.txt,.md" ... />
```

---

## 🗄️ Database migrations

The app uses `Base.metadata.create_all` by default (fine for development). For production schema versioning:

```bash
cd backend

# After changing a SQLAlchemy model
alembic revision --autogenerate -m "add tags column to documents"
alembic upgrade head

# Or set USE_ALEMBIC=true in .env to run migrations on startup
```

---

## 🐛 Debugging tips

**Backend 500 on `/api/query/`**
→ Check `docker logs enterprise-knowledge-assistant-backend-1`
→ Usually a missing API key or model download permission issue

**`PermissionError at /nonexistent` in logs**
→ HuggingFace cache path issue — ensure `HF_HOME=/app/data/hf_cache` is set in Dockerfile ENV

**Frontend shows "Login failed"**
→ Backend container crashed — check logs, usually a bcrypt or DB connection issue

**`passlib` errors**
→ We removed passlib — use `bcrypt` directly. See `auth_service.py`.

**ChromaDB `vector_store: disconnected` in health check**
→ Normal on fresh start — ChromaDB initializes lazily on first document upload

---

## 📦 Dependency philosophy

- Pin exact versions in `requirements.txt` — no `>=` ranges
- Prefer well-maintained packages with recent releases
- ML packages: use CPU-only torch (`torch==x.x.x+cpu`) to keep image size manageable
- No `passlib` — it's unmaintained and caused bcrypt compatibility crashes
- Frontend: keep `package-lock.json` committed and use `npm ci` (not `npm install`) in CI
