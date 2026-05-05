# Enterprise Knowledge Assistant

AI-powered internal knowledge base using Retrieval-Augmented Generation (RAG) with department-based access control, multi-LLM support, and a modern React frontend.

## Features

- **RAG Pipeline** - Document ingestion, chunking, embedding, and retrieval-augmented generation
- **Multi-LLM Support** - OpenAI (GPT-4o-mini), Anthropic Claude, and Google Gemini
- **Department-based RBAC** - Three-tier access control (Employee, Admin, Super Admin)
- **Document Management** - Upload and process PDF, DOCX, and TXT files
- **Google OAuth + JWT** - Secure authentication with PKCE flow
- **Query History** - Full audit trail with confidence scores and source citations
- **Rate Limiting** - Per-endpoint configurable request throttling
- **Health Monitoring** - System health endpoint with component status

## Architecture

```
                    +------------------+
                    |  React Frontend  |
                    |  (Vite + TS)     |
                    +--------+---------+
                             |
                             | HTTP/REST
                             v
                    +------------------+
                    |  FastAPI Backend  |
                    |  (Python 3.12)   |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
     +--------+---+  +------+------+  +----+-----+
     |  PostgreSQL |  |  ChromaDB   |  |   LLM    |
     |  (Users,    |  |  (Vectors,  |  | Provider |
     |   Docs,     |  |   Chunks)   |  | (OpenAI/ |
     |   History)  |  |             |  |  Claude/ |
     +-------------+  +-------------+  |  Gemini) |
                                       +----------+
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ (or Docker)
- An API key for at least one LLM provider (OpenAI, Anthropic, or Google)

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd enterprise-knowledge-assistant

# Copy environment template
cp .env.example .env
# Edit .env with your API keys and settings
```

### 2. Run with Docker Compose (Recommended)

```bash
docker-compose up -d
```

This starts PostgreSQL and the backend API. The backend is available at `http://localhost:8000`.

### 3. Run Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend available at `http://localhost:5173`.

### 4. Run Backend Locally (Alternative)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start the server (requires PostgreSQL running)
uvicorn app.main:app --reload --port 8000
```

### Default Credentials

On first startup the app seeds a default admin account:
- Email: `admin@enterprise.com`
- Password: `admin123`

## Configuration

### LLM Provider Selection

Set `LLM_PROVIDER` in your `.env` file:

| Provider | Value | Model | Cost |
|----------|-------|-------|------|
| OpenAI | `openai` | gpt-4o-mini | Pay-per-token |
| Anthropic | `claude` | claude-sonnet-4-20250514 | Pay-per-token |
| Google | `gemini` | gemini-2.0-flash | Free tier available |

### Embedding Provider

Set `EMBEDDING_PROVIDER` in your `.env` file:

| Provider | Value | Model | Notes |
|----------|-------|-------|-------|
| Sentence Transformers | `sentence_transformers` | all-MiniLM-L6-v2 | Free, local, 384-dim |
| OpenAI | `openai` | text-embedding-3-small | API-based, 1536-dim |

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `SECRET_KEY` | Yes | - | JWT signing key (use `openssl rand -hex 32`) |
| `LLM_PROVIDER` | No | `openai` | LLM provider choice |
| `OPENAI_API_KEY` | If using OpenAI | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | If using Claude | - | Anthropic API key |
| `GEMINI_API_KEY` | If using Gemini | - | Google AI API key |
| `EMBEDDING_PROVIDER` | No | `sentence_transformers` | Embedding model provider |
| `GOOGLE_CLIENT_ID` | For OAuth | - | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | For OAuth | - | Google OAuth client secret |
| `FRONTEND_URL` | No | `http://localhost:5173` | Frontend URL for CORS/OAuth |
| `USE_ALEMBIC` | No | `false` | Use Alembic migrations instead of auto-create |

## Project Structure

```
enterprise-knowledge-assistant/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   │   ├── auth.py       # Authentication endpoints
│   │   │   ├── documents.py  # Document upload/management
│   │   │   ├── query.py      # RAG query endpoint
│   │   │   └── admin.py      # Admin operations
│   │   ├── core/             # RAG engine components
│   │   │   ├── rag_engine.py       # Orchestrator
│   │   │   ├── vector_store.py     # ChromaDB integration
│   │   │   ├── embeddings.py       # Embedding providers
│   │   │   ├── llm_client.py       # LLM provider abstraction
│   │   │   └── document_processor.py  # Parse & chunk
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic (auth)
│   │   ├── middleware/       # Auth & rate limiting
│   │   ├── config.py         # App settings
│   │   ├── database.py       # Database session management
│   │   └── main.py           # FastAPI app entry point
│   ├── alembic/              # Database migrations
│   ├── tests/                # Backend test suite
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main React component
│   │   ├── api.ts            # Axios API client
│   │   └── types.ts          # TypeScript interfaces
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite configuration
├── .github/workflows/        # CI/CD pipeline
├── Dockerfile                # Backend container
├── docker-compose.yml        # Multi-service orchestration
└── .env.example              # Environment template
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | No | Register new user |
| POST | `/api/auth/login` | No | Login with email/password |
| POST | `/api/auth/refresh` | No | Refresh access token |
| GET | `/api/auth/me` | Yes | Get current user profile |
| GET | `/api/auth/google/login` | No | Initiate Google OAuth |
| POST | `/api/query/` | Yes | Ask a question (RAG) |
| GET | `/api/query/history` | Yes | Get query history |
| POST | `/api/documents/upload` | Admin | Upload a document |
| GET | `/api/documents/` | Yes | List documents (RBAC filtered) |
| DELETE | `/api/documents/{id}` | Admin | Delete a document |
| GET | `/api/admin/departments` | Admin | List departments |
| POST | `/api/admin/departments` | Admin | Create department |
| GET | `/api/admin/stats` | Admin | System statistics |
| GET | `/api/health` | No | Health check |

Interactive API docs available at `http://localhost:8000/docs` (Swagger UI).

## Database Migrations

The app auto-creates tables on startup by default. For production deployments with schema versioning:

```bash
cd backend

# Set environment variable
export USE_ALEMBIC=true

# Run migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "description"
```

## Testing

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Full RAG pipeline test (requires LLM API key)
python -m tests.test_rag_pipeline --full

# Frontend lint and build
cd frontend
npm run lint
npm run build
```

## Docker Deployment

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

The backend includes a health check at `/api/health` that reports database, vector store, and LLM provider status.

## Security

- Passwords hashed with bcrypt
- JWT access tokens (60-min expiry) + refresh tokens (7-day expiry)
- Google OAuth with PKCE (S256) and signed state tokens
- Per-endpoint rate limiting
- RBAC enforced at middleware and endpoint levels
- Non-root Docker container user

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT
