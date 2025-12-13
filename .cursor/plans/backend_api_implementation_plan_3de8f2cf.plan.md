---
name: Backend API Implementation Plan
overview: "Build FastAPI backend server connecting React frontend to production-ready infrastructure: Pinecone (vector DB), PostgreSQL (Render), AWS S3, Clerk auth, with LangChain chunking and OpenAI embeddings."
todos:
  - id: update-dependencies
    content: Add FastAPI, Uvicorn, SQLAlchemy, Alembic, Pinecone, and JWT dependencies to requirements.txt
    status: completed
  - id: update-settings
    content: Update src/config/settings.py with database URL, Clerk secret key, Pinecone config, and text-embedding-3-large as default embedding model
    status: completed
  - id: migrate-chunking
    content: Replace custom TextChunker with LangChain RecursiveCharacterTextSplitter in src/ingestion/chunking.py
    status: completed
  - id: create-pinecone-store
    content: Create src/rag/pinecone_store.py with Pinecone Serverless integration (3072 dimensions for text-embedding-3-large)
    status: completed
  - id: update-vector-store
    content: Update src/rag/vector_store.py to use Pinecone instead of ChromaDB
    status: completed
  - id: database-connection
    content: Create src/database/db.py with SQLAlchemy engine, session management, and FastAPI dependency
    status: completed
  - id: database-models
    content: Create src/database/models.py with User, Document, Insight, TrainingStatus, and Integration models
    status: completed
  - id: alembic-setup
    content: Initialize Alembic and create initial database migration
    status: completed
  - id: fastapi-server
    content: Create src/api/server.py with FastAPI app, CORS configuration, and health check endpoint
    status: completed
  - id: auth-dependencies
    content: Create src/api/dependencies.py with get_current_user (Clerk JWT verification) and get_db dependencies
    status: completed
  - id: documents-router
    content: Implement documents API router with list, upload, get, delete, search, preview, and status endpoints
    status: completed
  - id: insights-router
    content: Implement insights API router with list, create, update, delete, voice upload, and search endpoints
    status: completed
  - id: training-router
    content: Implement training API router with status, complete, and stats endpoints
    status: completed
  - id: integrate-services
    content: Connect API endpoints to DocumentIngester, IngestionPipeline, Pinecone, and S3 services
    status: completed
  - id: local-env-setup
    content: Create .env.local with all required environment variables for local development
    status: completed
  - id: render-deployment
    content: Set up Render PostgreSQL database and Web Service, configure environment variables, and deploy
    status: completed
  - id: pinecone-indexes
    content: Create Pinecone indexes (youtopia-dev and youtopia-prod) with 3072 dimensions for text-embedding-3-large
    status: completed
---

# Backend API Implementation Plan

## Architecture Overview

**Component Stack:**

- **Frontend**: React app on Vercel ✅
- **Backend API**: FastAPI on Render
- **Authentication**: Clerk ✅
- **Vector Database**: Pinecone Serverless (local & production)
- **File Storage**: AWS S3 ✅
- **Metadata Database**: PostgreSQL on Render
- **Embeddings**: OpenAI text-embedding-3-large
- **Chunking**: LangChain Text Splitters

## Current State

### ✅ What Exists

**Frontend (Complete)**

- React app with full UI
- API client expecting `/api/clone/*` endpoints
- Clerk authentication integrated
- TypeScript types defined

**Backend Infrastructure (Partial)**

- Document ingestion pipeline
- S3 client for file storage
- OpenAI LLM client
- Personality analysis
- Logging utilities
- Settings management

### ❌ What's Missing

**Backend API Server**

- No FastAPI application
- No API endpoints
- No database layer
- No Clerk token verification
- No Pinecone integration
- Custom chunking (needs LangChain migration)

## Implementation Plan

### Phase 1: Foundation & Dependencies

**1.1 Update Dependencies (`requirements.txt`)**

Add:

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
pinecone-client==3.0.0
langchain-text-splitters==0.3.0  # If separate package, or use existing langchain
```

**1.2 Update Configuration (`src/config/settings.py`)**

Add new settings:

```python
# Database
database_url: str = Field(..., env="DATABASE_URL")

# Clerk
clerk_secret_key: str = Field(..., env="CLERK_SECRET_KEY")

# Pinecone
pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
pinecone_index_name: str = Field("youtopia-dev", env="PINECONE_INDEX_NAME")

# Embeddings (update default)
openai_embedding_model: str = Field("text-embedding-3-large", env="OPENAI_EMBEDDING_MODEL")
```

**1.3 Migrate Chunking to LangChain (`src/ingestion/chunking.py`)**

Replace custom `TextChunker` with LangChain's `RecursiveCharacterTextSplitter`:

- Use `langchain.text_splitter.RecursiveCharacterTextSplitter`
- Maintain same interface (chunk_text, chunk_texts methods)
- Preserve metadata handling
- Use chunk_size and chunk_overlap from settings

**1.4 Create Pinecone Vector Store (`src/rag/pinecone_store.py`)**

Create new Pinecone wrapper:

- Initialize Pinecone client with API key
- Create/get index (3072 dimensions for text-embedding-3-large)
- Implement `add_texts()`, `search()`, `delete()` methods
- Match interface of existing `VectorStore` class
- Handle index creation if it doesn't exist

**1.5 Update Vector Store Usage**

Replace `src/rag/vector_store.py` to use Pinecone:

- Remove ChromaDB dependency
- Import and use `PineconeStore`
- Keep same public interface for backward compatibility

### Phase 2: Database Layer

**2.1 Database Connection (`src/database/db.py`)**

Create:

- SQLAlchemy engine with connection pooling
- Session factory
- Database dependency for FastAPI
- Support for PostgreSQL (production) and SQLite (local dev)

**2.2 Database Models (`src/database/models.py`)**

Create SQLAlchemy models:

- `User`: id, clerk_user_id, created_at, updated_at
- `Document`: id, user_id, name, size, type, status, s3_key, chunks_count, uploaded_at, error_message
- `Insight`: id, user_id, content, type, audio_url, transcription_id, created_at, updated_at
- `TrainingStatus`: user_id (PK), is_complete, progress, documents_count, insights_count, integrations_count, thresholds_json, achievements_json
- `Integration`: id, user_id, type, status, credentials_encrypted, last_sync_at, sync_settings_json

**2.3 Database Migrations**

- Initialize Alembic: `alembic init alembic`
- Configure `alembic/env.py` with database URL
- Create initial migration: `alembic revision --autogenerate -m "initial"`
- Apply migration: `alembic upgrade head`

### Phase 3: FastAPI Server

**3.1 Main Application (`src/api/server.py`)**

Create FastAPI app:

- Initialize FastAPI instance
- Configure CORS (allow Vercel frontend origin)
- Include routers
- Health check endpoint (`/health`)
- Error handling middleware

**3.2 Authentication (`src/api/dependencies.py`)**

Create dependencies:

- `get_current_user()`: Verifies Clerk JWT token, extracts user_id
- `get_db()`: Database session dependency
- Handle authentication errors gracefully

**3.3 API Routers**

**Documents Router (`src/api/routers/documents.py`):**

- `GET /api/clone/documents` - List user's documents
- `POST /api/clone/documents` - Upload document (multipart/form-data)
- `GET /api/clone/documents/{id}` - Get document details
- `GET /api/clone/documents/{id}/preview` - Get S3 presigned URL
- `GET /api/clone/documents/{id}/status` - Get processing status
- `DELETE /api/clone/documents/{id}` - Delete document
- `GET /api/clone/documents/search` - Search documents

**Insights Router (`src/api/routers/insights.py`):**

- `GET /api/clone/insights` - List user's insights
- `POST /api/clone/insights` - Create text insight
- `POST /api/clone/insights/voice` - Upload voice recording
- `PUT /api/clone/insights/{id}` - Update insight
- `DELETE /api/clone/insights/{id}` - Delete insight
- `GET /api/clone/insights/search` - Search insights

**Training Router (`src/api/routers/training.py`):**

- `GET /api/clone/training/status` - Get training status
- `POST /api/clone/training/complete` - Mark training complete
- `GET /api/clone/training/stats` - Get training statistics

### Phase 4: Integration with Existing Services

**4.1 Document Upload Flow**

1. Receive file upload in FastAPI endpoint
2. Save file to S3 (using existing `S3Client`)
3. Create `Document` record in database (status: "pending")
4. Process document asynchronously:

   - Extract text using `DocumentIngester`
   - Chunk using LangChain `TextChunker`
   - Generate embeddings using `EmbeddingService` (text-embedding-3-large)
   - Store chunks in Pinecone
   - Update document status to "complete" with chunks_count

5. Return document metadata to frontend

**4.2 Training Status Calculation**

- Query database for user's documents, insights, integrations
- Calculate progress based on thresholds
- Update `TrainingStatus` record
- Return status to frontend

### Phase 5: Local Development Setup

**5.1 Environment Variables (`.env.local`)**

```bash
# Database (SQLite for local)
DATABASE_URL=sqlite:///./data/youtopia.db

# Clerk
CLERK_SECRET_KEY=sk_test_...

# Pinecone (free tier)
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=youtopia-dev

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# AWS S3
S3_BUCKET_NAME=youtopia-mind-data
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

**5.2 Run Locally**

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000
```

**5.3 Frontend Configuration**

Update `frontend/.env.local`:

```bash
VITE_API_URL=http://localhost:8000
```

### Phase 6: Render Deployment

**6.1 Create Render Services**

1. **PostgreSQL Database**:

   - Create new PostgreSQL database on Render
   - Note the connection string (auto-provided as `DATABASE_URL`)

2. **Web Service**:

   - Create new Web Service
   - Connect GitHub repository
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn src.api.server:app --host 0.0.0.0 --port $PORT`

**6.2 Environment Variables on Render**

Set in Render dashboard:

- `DATABASE_URL` (auto-provided by Render PostgreSQL)
- `CLERK_SECRET_KEY`
- `PINECONE_API_KEY` (production Pinecone key)
- `PINECONE_INDEX_NAME=youtopia-prod`
- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL=text-embedding-3-large`
- `S3_BUCKET_NAME`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION=us-east-1`

**6.3 Pinecone Index Setup**

1. Create Pinecone index:

   - Name: `youtopia-prod`
   - Dimensions: 3072 (for text-embedding-3-large)
   - Metric: cosine
   - Serverless tier

2. For local dev, create separate index:

   - Name: `youtopia-dev`
   - Same configuration

**6.4 Deploy**

- Push to main branch triggers automatic deployment
- Run migrations on first deploy: `alembic upgrade head`
- Update frontend `VITE_API_URL` to Render URL

## File Structure

### New Files to Create

```
src/
├── api/
│   ├── __init__.py
│   ├── server.py              # FastAPI app
│   ├── dependencies.py        # Auth & DB dependencies
│   └── routers/
│       ├── __init__.py
│       ├── documents.py
│       ├── insights.py
│       └── training.py
├── database/
│   ├── __init__.py
│   ├── db.py                  # Database connection
│   └── models.py             # SQLAlchemy models
└── rag/
    └── pinecone_store.py     # Pinecone wrapper

alembic/
├── env.py                    # Alembic config
└── versions/
    └── 001_initial.py        # Initial migration
```

### Files to Modify

- `requirements.txt` - Add new dependencies
- `src/config/settings.py` - Add database, Clerk, Pinecone config
- `src/ingestion/chunking.py` - Replace with LangChain
- `src/rag/vector_store.py` - Use Pinecone instead of ChromaDB
- `src/rag/embeddings.py` - Already correct (uses settings)

## Key Implementation Details

### Pinecone Index Configuration

- **Dimensions**: 3072 (text-embedding-3-large)
- **Metric**: cosine
- **Index Type**: Serverless
- **Local Index**: `youtopia-dev`
- **Production Index**: `youtopia-prod`

### Database Schema Highlights

- All tables include `user_id` for multi-tenancy
- `Document.status` tracks: "pending", "processing", "complete", "error"
- `TrainingStatus` calculated from actual counts in database
- JSON fields for flexible metadata storage

### Error Handling

- Return consistent error responses
- Log errors with context
- Handle S3, Pinecone, and database errors gracefully
- Validate file uploads (size, type)

### Security

- Verify Clerk JWT tokens on every request
- Validate user ownership of resources
- Sanitize file uploads
- Use environment variables for secrets

## Testing Checklist

- [ ] Document upload and processing
- [ ] Document list and search
- [ ] Insight creation (text and voice)
- [ ] Training status calculation
- [ ] Clerk authentication
- [ ] Database migrations
- [ ] Pinecone integration
- [ ] S3 file storage
- [ ] Error handling

## Next Steps

1. Install dependencies and update configuration
2. Migrate chunking to LangChain
3. Set up Pinecone integration
4. Create database models and migrations
5. Build FastAPI server with authentication
6. Implement core API endpoints
7. Test locally
8. Deploy to Render