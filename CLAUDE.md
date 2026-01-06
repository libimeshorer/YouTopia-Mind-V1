# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTopia Mind is a multi-tenant AI clone platform that creates personalized AI assistants. Users upload documents/data, which gets processed into vector embeddings, enabling AI clones to respond in a personalized manner.

## Development Commands

### Frontend (from `/frontend` directory)
```bash
npm run dev          # Start dev server on port 8080
npm run build        # Production build
npm run lint         # Run ESLint
```

### Backend
```bash
uvicorn src.api.server:app --reload    # Start FastAPI dev server on port 8000
pytest tests/                           # Run test suite
alembic upgrade head                    # Run database migrations
python scripts/check_environment.py     # Validate environment configuration
```

### Docker (for local PostgreSQL)
```bash
docker-compose up -d    # Start PostgreSQL and pgAdmin
```

### Startup Script
```bash
./start.sh    # Runs migrations then starts FastAPI server (used by Render)
```

## Architecture

### Technology Stack
- **Backend**: FastAPI, PostgreSQL (Render), Pinecone (vector DB), OpenAI API, SQLAlchemy/Alembic, LangChain
- **Frontend**: React 18 + TypeScript, Vite, TailwindCSS + shadcn/ui, Clerk (auth)

### Multi-Tenant Hierarchy
```
Tenant (Organization)
  └── Clone (AI persona)
        └── Session (conversation)
              └── Message
```

### Key Backend Modules
- `src/api/routers/` - FastAPI route handlers (chat, documents, insights, training, integrations)
- `src/database/models.py` - SQLAlchemy models (Tenant, Clone, Session, Message, Document)
- `src/rag/` - RAG pipeline: vector_store, retriever, embeddings, clone_vector_store
- `src/ingestion/` - Data ingestion: documents, Slack, emails
- `src/llm/` - OpenAI client and prompt building with personality context
- `src/services/` - Business logic (chat_service, session_manager)

### Key Frontend Structure
- `frontend/src/pages/` - Route pages (Dashboard, Chat, Training, Activity)
- `frontend/src/components/ui/` - shadcn/ui components
- `frontend/src/api/` - API client with Clerk auth token injection

## Critical Patterns

### Data Isolation
Every operation must include `clone_id` and `tenant_id`. CloneVectorStore enforces clone-specific vector retrieval. This is essential for multi-tenant security.

### Environment Safety
- Two environments: `development` and `production` (defaults to development)
- Destructive operations blocked in production
- Environment validated at startup via `src/utils/environment.py`
- Use `.dev.env` for development, `.prod.env` for production

### Authentication Flow
- Clerk handles frontend auth, issues JWT tokens
- Backend validates Clerk tokens in `src/api/dependencies.py`
- `CloneContext` object carries authenticated user/tenant/clone info through requests

### RAG Pipeline Flow
Document → Chunking → Embeddings → Pinecone storage → Retrieval with clone_id filter → Prompt augmentation with personality profile

## Environment Variables

Key variables (see `.dev.env` for full list):
- `ENVIRONMENT` - development/production
- `DATABASE_URL` - PostgreSQL connection
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`
- `CLERK_SECRET_KEY` (backend), `VITE_CLERK_PUBLISHABLE_KEY` (frontend)
- `S3_BUCKET_NAME`, AWS credentials

## Database

- PostgreSQL with UUID primary keys (Sessions use BIGSERIAL)
- Cascading deletes for data cleanup
- Migrations in `alembic/versions/`
