<div align="center">

# 🧠 Enterprise Knowledge Assistant

**Ask your company anything. Get cited, confident answers in seconds.**

*AI-powered internal search built on RAG — with department security, multi-LLM support, and a premium dark UI.*

[![CI](https://github.com/M33HA1/enterprise-knowledge-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/M33HA1/enterprise-knowledge-assistant/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## 🤔 What is this?

Imagine your company has hundreds of policy documents, engineering guidelines, HR handbooks, and SOPs. Finding the right answer means digging through folders, pinging colleagues, or just guessing.

**EKA fixes that.** Upload your documents once. Ask questions in plain English. Get back precise, cited answers — with confidence scores and escalation flags when the AI isn't sure.

```
You:  "What's our PTO policy after 3 years?"

EKA:  According to the Employee Handbook v3.2 (HR dept, p.4):
      Employees with 3+ years receive 20 days of PTO annually...
      
      📎 Source: employee_handbook.txt  |  Confidence: 92%  |  ✅ No escalation needed
```

---

## ✨ What makes it special?

| Feature | What it means for you |
|---|---|
| 🔒 **Department RBAC** | HR docs stay in HR. Engineering docs stay in Engineering. |
| 🤖 **3 LLM providers** | OpenAI, Claude, or Gemini — swap with one env var |
| 📄 **PDF / DOCX / TXT** | Upload any internal document, indexed in seconds |
| 🔑 **Google OAuth + JWT** | Sign in with your company Google account |
| 📊 **Confidence scores** | Know when to trust the answer vs. escalate to a human |
| 🕐 **Full query history** | Audit trail of every question asked |
| 🐳 **One-command deploy** | `docker-compose up` and you're live |

---

## 🏗️ How it works

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Browser                            │
│              React + TypeScript + Tailwind                  │
└──────────────────────┬──────────────────────────────────────┘
                       │  REST API
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                           │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   Auth   │  │Documents │  │  Query   │  │  Admin   │     │
│  │  + JWT   │  │ + Upload │  │  + RAG   │  │  + RBAC  │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  RAG Pipeline                       │    │
│  │  Document → Chunk → Embed → Store → Retrieve → LLM  │    │
│  └─────────────────────────────────────────────────────┘    │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │   ChromaDB   │  │  LLM API     │
│  Users/Docs  │  │  Embeddings  │  │  OpenAI /    │
│  History     │  │  Vectors     │  │  Claude /    │
└──────────────┘  └──────────────┘  │  Gemini      │
                                    └──────────────┘
```

**The RAG pipeline in plain English:**
1. You upload a PDF → it gets split into ~500-char chunks
2. Each chunk gets converted to a 384-dimension vector (semantic fingerprint)
3. Vectors are stored in ChromaDB with department metadata
4. When you ask a question → your question becomes a vector too
5. The 5 most similar chunks are retrieved (filtered by your department)
6. Those chunks + your question go to the LLM → cited answer comes back

---

## 🚀 Get running in 3 minutes

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- An API key from one of: [OpenAI](https://platform.openai.com/api-keys) · [Anthropic](https://console.anthropic.com/) · [Google AI Studio](https://aistudio.google.com/apikey) (free)

### Step 1 — Clone and configure

```bash
git clone https://github.com/M33HA1/enterprise-knowledge-assistant.git
cd enterprise-knowledge-assistant
cp .env.example .env
```

Open `.env` and set your API key. The fastest way to get started is Gemini (free tier):

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
```

### Step 2 — Start everything

```bash
docker-compose up --build
```

> ☕ First build takes ~5 minutes (downloads ML models). Subsequent starts are instant.

### Step 3 — Open the app

| Service | URL |
|---|---|
| 🖥️ Frontend | http://localhost:5173 |
| 🔧 Backend API | http://localhost:8000 |
| 📖 API Docs | http://localhost:8000/docs |

**Default login:**
```
Email:    admin@enterprise.com
Password: admin123
```

### Step 4 — Upload a document and ask something

1. Go to **Documents** tab → upload any PDF, DOCX, or TXT
2. Switch to **Chat** tab → ask a question about it
3. Watch the cited answer appear with confidence score and sources

---

## ⚙️ Configuration

### Choosing your LLM

Set `LLM_PROVIDER` in `.env`:

```bash
# Free tier — recommended for development
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key

# Best quality
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Alternative
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

| Provider | Model | Cost | Best for |
|---|---|---|---|
| `gemini` | gemini-2.0-flash | **Free tier** (15 RPM) | Development |
| `openai` | gpt-4o-mini | ~$0.15/1M tokens | Production |
| `claude` | claude-3-5-sonnet | ~$3/1M tokens | High accuracy |

### All environment variables

<details>
<summary>Click to expand full .env reference</summary>

```bash
# ── Required ──────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_assistant
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">

# ── LLM (pick one) ────────────────────────────────────────────
LLM_PROVIDER=gemini          # openai | claude | gemini
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...

# ── Embeddings ────────────────────────────────────────────────
EMBEDDING_PROVIDER=sentence_transformers   # free, local
# EMBEDDING_PROVIDER=openai               # paid, higher quality

# ── Google OAuth (optional) ───────────────────────────────────
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# ── Tuning ────────────────────────────────────────────────────
CHUNK_SIZE=500               # characters per document chunk
CHUNK_OVERLAP=50             # overlap between chunks
TOP_K_RESULTS=5              # chunks retrieved per query
CONFIDENCE_THRESHOLD=0.3     # below this → escalation flag
```

</details>

---

## 📁 Project structure

```
enterprise-knowledge-assistant/
│
├── 🐳 Dockerfile                    # Backend container (Python 3.12)
├── 🐳 docker-compose.yml            # Orchestrates db + backend + frontend
├── 🔑 .env.example                  # Copy this to .env
│
├── backend/
│   ├── app/
│   │   ├── 🚪 main.py               # FastAPI app, startup, CORS
│   │   ├── ⚙️  config.py             # All settings via Pydantic
│   │   ├── 🗄️  database.py           # Async SQLAlchemy engine
│   │   │
│   │   ├── api/                     # HTTP route handlers
│   │   │   ├── auth.py              # Login, register, OAuth, JWT refresh
│   │   │   ├── documents.py         # Upload, list, delete documents
│   │   │   ├── query.py             # RAG query + history
│   │   │   └── admin.py             # Users, departments, stats
│   │   │
│   │   ├── core/                    # The RAG engine
│   │   │   ├── rag_engine.py        # Orchestrator (ingest + query)
│   │   │   ├── document_processor.py # Parse PDF/DOCX/TXT → chunks
│   │   │   ├── embeddings.py        # sentence-transformers / OpenAI
│   │   │   ├── vector_store.py      # ChromaDB wrapper + RBAC filter
│   │   │   └── llm_client.py        # OpenAI / Claude / Gemini clients
│   │   │
│   │   ├── models/                  # SQLAlchemy ORM (User, Document, etc.)
│   │   ├── schemas/                 # Pydantic request/response models
│   │   ├── services/                # auth_service (bcrypt, JWT)
│   │   └── middleware/              # JWT auth + rate limiting deps
│   │
│   ├── tests/                       # pytest test suite
│   ├── alembic/                     # DB migration scripts
│   └── requirements.txt
│
└── frontend/
    ├── 🐳 Dockerfile                # Node build + nginx serve
    ├── nginx.conf                   # SPA routing + /api proxy
    └── src/
        ├── App.tsx                  # Full app (sidebar layout, all views)
        ├── api.ts                   # Axios client + token refresh
        └── types.ts                 # TypeScript interfaces
```

---

## 🔌 API reference

All endpoints are also available interactively at **http://localhost:8000/docs**

### Authentication

```
POST /api/auth/register      Create account → returns token pair
POST /api/auth/login         Email + password → returns token pair
POST /api/auth/refresh       Refresh token → new access token
GET  /api/auth/me            Current user profile
GET  /api/auth/google/login  Start Google OAuth flow
POST /api/auth/oauth/exchange Exchange OAuth code → token pair
```

### Documents

```
POST   /api/documents/upload    Upload + ingest document  [Admin]
GET    /api/documents/          List documents (RBAC filtered)
GET    /api/documents/{id}      Get single document
DELETE /api/documents/{id}      Delete document + vectors  [Admin]
```

### Query

```
POST /api/query/         Ask a question → RAG answer with citations
GET  /api/query/history  Your query history (paginated)
```

### Admin

```
GET    /api/admin/departments        List all departments
POST   /api/admin/departments        Create department  [Admin]
DELETE /api/admin/departments/{id}   Delete department  [Super Admin]
GET    /api/admin/users              List all users  [Admin]
PATCH  /api/admin/users/{id}         Update user role/dept  [Admin]
GET    /api/admin/stats              System statistics  [Admin]
GET    /api/health                   Health check (no auth)
```

### Example: Ask a question

```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is our remote work policy?"}'
```

```json
{
  "answer": "According to the Employee Handbook, remote work is permitted up to 3 days per week...",
  "sources": [
    {
      "document": "employee_handbook.txt",
      "page": 1,
      "department": "hr",
      "relevance_score": 0.89
    }
  ],
  "confidence": 0.85,
  "needs_escalation": false,
  "model_used": "gemini-2.0-flash",
  "tokens_used": 412,
  "response_time_ms": 1243
}
```

---

## 👥 User roles

```
Super Admin  ──▶  Everything: manage users, departments, all documents
    │
    ▼
  Admin      ──▶  Upload/delete documents, view all departments
    │
    ▼
Employee     ──▶  Query documents in their own department only
```

**RBAC is enforced at two levels:**
- API middleware (JWT role check)
- Vector search (ChromaDB `where` filter on `department` metadata)

An Engineering employee literally cannot retrieve HR document chunks — the filter is applied before the LLM ever sees the context.

---

## 🧪 Testing

```bash
# Run all backend tests
cd backend
python -m pytest tests/ -v

# What's tested:
# ✅ requirements.txt formatting (no merged lines)
# ✅ Config values (valid model names, JWT settings)
# ✅ Startup validation (placeholder credential warnings)
# ✅ Document parsing and chunking
# ✅ Embedding model (384-dim vectors)
# ✅ Rate limiting logic
# ⏭️  Vector store + RAG (skipped without LLM API key)

# Frontend
cd frontend
npm run lint    # ESLint
npm run build   # TypeScript + Vite build
```

---

## 🐳 Docker reference

```bash
# Start everything (first time — builds images)
docker-compose up --build

# Start in background
docker-compose up -d

# View backend logs
docker-compose logs -f backend

# Rebuild just the backend (after code changes)
docker-compose up --build backend

# Stop everything
docker-compose down

# Stop and wipe all data (fresh start)
docker-compose down -v
```

**Volumes:**
| Volume | What's stored |
|---|---|
| `postgres_data` | All database data (users, docs, history) |
| `hf_cache` | Downloaded HuggingFace models (avoids re-download) |
| `./backend/data/uploads` | Uploaded document files |
| `./backend/data/chroma_db` | Vector embeddings |

---

## 🔒 Security notes

- Passwords hashed with **bcrypt** (work factor 12)
- JWT access tokens expire in **60 minutes**, refresh tokens in **7 days**
- Google OAuth uses **PKCE (S256)** + signed state tokens (CSRF protection)
- Rate limiting: 10 logins/min, 30 queries/min, 20 uploads/min per user
- Docker container runs as **non-root** `app` user
- `SECRET_KEY` and `GOOGLE_CLIENT_SECRET` validated at startup — warnings logged if placeholders detected

> ⚠️ **Before going to production:** generate a real `SECRET_KEY`, set `DEBUG=false`, and use a managed PostgreSQL instance.

---

## 🛠️ Extending the project

<details>
<summary>➕ Add a new LLM provider</summary>

1. Add enum value to `LLMProvider` in `backend/app/config.py`
2. Add API key + model fields to `Settings`
3. Create a class extending `BaseLLMClient` in `backend/app/core/llm_client.py`
4. Implement `generate()` and `agenerate()`
5. Add the case to `get_llm_client()` factory
6. Add the package to `requirements.txt`

</details>

<details>
<summary>➕ Add a new document type</summary>

1. Add the extension to `ALLOWED_EXTENSIONS` in `backend/app/api/documents.py`
2. Add a `_parse_xxx()` static method to `DocumentParser` in `document_processor.py`
3. Add the extension to the `accept` attribute in the frontend file input

</details>

<details>
<summary>➕ Add database migrations (Alembic)</summary>

```bash
cd backend

# After changing a model
alembic revision --autogenerate -m "add user avatar field"
alembic upgrade head

# Or set USE_ALEMBIC=true in .env to use migrations on startup
```

</details>

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development guide.

**Quick version:**
1. Fork → feature branch → PR to `main`
2. CI must pass (backend tests + frontend build + Docker build)
3. Use [conventional commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`

---

## 📄 License

MIT — use it, fork it, ship it.

---

<div align="center">

Built with FastAPI · React · ChromaDB · PostgreSQL · sentence-transformers

</div>
