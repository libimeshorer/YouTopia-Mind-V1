---
name: Backend Services Connection Testing
overview: Plan to connect and test all backend services (Pinecone, AWS S3, Render PostgreSQL, FastAPI) with comprehensive setup guides, connection tests, and integration verification.
todos:
  - id: setup_accounts
    content: Set up accounts and get credentials for Pinecone, AWS S3, Render PostgreSQL, and verify Clerk setup
    status: pending
  - id: create_env_file
    content: Create .env.local with all service credentials and verify settings.py loads them correctly
    status: pending
  - id: create_migrations
    content: Create initial Alembic migration for database schema and test on both SQLite and Render PostgreSQL
    status: pending
  - id: test_postgres
    content: Create and run PostgreSQL connection test script (test_postgres.py)
    status: pending
  - id: test_pinecone
    content: Create and run Pinecone connection test script (test_pinecone.py) - verify index creation and vector operations
    status: pending
  - id: test_s3
    content: Create and run AWS S3 connection test script (test_s3.py) - verify bucket access and file operations
    status: pending
  - id: test_fastapi
    content: Create and run FastAPI server test script (test_fastapi.py) - verify server startup and endpoints
    status: pending
  - id: test_e2e_document
    content: Create and run end-to-end document upload test (test_e2e_document_upload.py) - full flow from API to S3 to Pinecone
    status: pending
  - id: deploy_render
    content: Deploy FastAPI server to Render, configure environment variables, and verify deployment
    status: pending
  - id: verify_production
    content: Run all connection tests against production services and verify end-to-end functionality
    status: pending
---

# Backend Services Connection Testing Plan

## Overview

This plan covers setting up accounts, configuring credentials, creating database migrations, and testing connections to all backend services: Pinecone (vector DB), AWS S3 (file storage), Render (PostgreSQL + FastAPI hosting), and Clerk (authentication).

## Phase 1: Service Account Setup & Credentials

### 1.1 Pinecone Setup

- Create Pinecone account at https://pinecone.io
- Get API key from dashboard
- Create two indexes:
  - `youtopia-dev` (3072 dimensions, cosine, serverless)
  - `youtopia-prod` (3072 dimensions, cosine, serverless)
- Document API key and index names

### 1.2 AWS S3 Setup

- Create AWS account or use existing
- Create S3 bucket: `youtopia-mind-data` (or custom name)
- Create IAM user with S3 access:
  - Policy: `AmazonS3FullAccess` (or custom policy for specific bucket)
- Generate access key ID and secret access key
- Document bucket name, region, and credentials

### 1.3 Render Setup

- Create Render account at https://render.com
- Create PostgreSQL database:
  - Name: `youtopia-mind-db`
  - Region: Choose closest to users
  - Note the `DATABASE_URL` connection string
- Prepare for Web Service deployment (Phase 4)

### 1.4 Clerk Setup (if not done)

- Verify Clerk account exists
- Get secret key from Clerk dashboard
- Get frontend API URL, issuer, and audience
- Document all Clerk credentials

## Phase 2: Environment Configuration

### 2.1 Create Local Environment File

Create `.env.local` in project root with all credentials:

```bash
# Database
DATABASE_URL=sqlite:///./data/youtopia.db  # Local dev
# For production: Use Render DATABASE_URL

# Clerk
CLERK_SECRET_KEY=sk_test_...
CLERK_FRONTEND_API=https://your-domain.clerk.accounts.dev
CLERK_ISSUER=https://your-domain.clerk.accounts.dev
CLERK_AUDIENCE=your-audience

# Pinecone
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=youtopia-dev  # Use youtopia-prod for production

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# AWS S3
S3_BUCKET_NAME=youtopia-mind-data
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### 2.2 Update Settings Validation

- Verify `src/config/settings.py` handles all required variables
- Make Slack variables optional (not required for API server)
- Test settings loading with missing variables

## Phase 3: Database Migrations

### 3.1 Create Initial Migration

- Run `alembic revision --autogenerate -m "initial_schema"`
- Review generated migration in `alembic/versions/`
- Verify all models are included: User, Document, Insight, TrainingStatus, Integration
- Fix any issues (UUID types, relationships, etc.)

### 3.2 Test Migration Locally

- Create local SQLite database: `mkdir -p data`
- Run `alembic upgrade head`
- Verify tables created correctly
- Test rollback: `alembic downgrade -1` then `alembic upgrade head`

### 3.3 Test Migration on Render PostgreSQL

- Set `DATABASE_URL` to Render PostgreSQL connection string
- Run `alembic upgrade head` against production database
- Verify tables created in Render dashboard

## Phase 4: Connection Testing Scripts

### 4.1 Create Test Script Structure

Create `tests/test_connections.py` with test functions for each service:

**PostgreSQL Connection Test:**

- Connect using SQLAlchemy engine
- Create test query (SELECT 1)
- Verify connection pooling works
- Test transaction rollback

**Pinecone Connection Test:**

- Initialize Pinecone client
- Verify index exists or create it
- Test upsert operation (add test vector)
- Test query operation
- Test delete operation
- Verify dimension matches (3072)

**AWS S3 Connection Test:**

- Initialize S3 client
- Test bucket exists and is accessible
- Test upload small test file
- Test download test file
- Test delete test file
- Test presigned URL generation

**FastAPI Server Test:**

- Start server locally
- Test `/health` endpoint
- Test CORS headers
- Test authentication endpoint (with mock token)

### 4.2 Create Integration Test Script

Create `scripts/test_backend_integration.py`:

- Test full document upload flow:

  1. Upload document via API
  2. Verify document in database
  3. Verify file in S3
  4. Verify chunks in Pinecone
  5. Test document retrieval
  6. Test document deletion

## Phase 5: Service-Specific Connection Tests

### 5.1 PostgreSQL (Render) Test

**File:** `scripts/test_postgres.py`

- Connect to Render PostgreSQL
- Test table creation/querying
- Test user creation and retrieval
- Test document CRUD operations
- Measure connection latency
- Test connection pooling

### 5.2 Pinecone Test

**File:** `scripts/test_pinecone.py`

- Test index creation (if doesn't exist)
- Test embedding generation (verify 3072 dimensions)
- Test vector upsert (batch and single)
- Test similarity search
- Test metadata filtering
- Test vector deletion
- Measure query latency
- Test index stats retrieval

### 5.3 AWS S3 Test

**File:** `scripts/test_s3.py`

- Test bucket access permissions
- Test file upload (various sizes)
- Test file download
- Test presigned URL generation (1 hour expiry)
- Test file deletion
- Test listing objects with prefix
- Test error handling (non-existent file, permission errors)
- Verify file integrity (checksums)

### 5.4 FastAPI Server Test

**File:** `scripts/test_fastapi.py`

- Test server startup
- Test health endpoint
- Test CORS configuration
- Test authentication middleware
- Test database dependency injection
- Test error handling
- Test request/response logging

## Phase 6: End-to-End Integration Testing

### 6.1 Document Upload Flow Test

**File:** `scripts/test_e2e_document_upload.py`

- Create test user (via Clerk token or direct DB)
- Upload PDF document via POST `/api/clone/documents`
- Verify:
  - Document record in PostgreSQL
  - File stored in S3
  - Chunks extracted and stored in Pinecone
  - Document status updates correctly
- Test document retrieval
- Test document preview (presigned URL)
- Test document deletion (cascades to S3 and Pinecone)

### 6.2 Training Status Flow Test

**File:** `scripts/test_e2e_training.py`

- Create user with documents and insights
- Test GET `/api/clone/training/status`
- Verify progress calculation
- Test training completion
- Verify thresholds and achievements

### 6.3 Authentication Flow Test

**File:** `scripts/test_e2e_auth.py`

- Test Clerk JWT token verification
- Test user creation on first login
- Test protected endpoints require auth
- Test user isolation (users can't access each other's data)

## Phase 7: Render Deployment Preparation

### 7.1 Update Requirements

- Verify `requirements.txt` has all dependencies
- Test installation: `pip install -r requirements.txt`
- Check for version conflicts

### 7.2 Create Render Configuration

- Create `render.yaml` (optional) for infrastructure as code
- Document build command: `pip install -r requirements.txt`
- Document start command: `uvicorn src.api.server:app --host 0.0.0.0 --port $PORT`
- Document environment variables needed

### 7.3 Test Local Production Build

- Set environment to production mode
- Test with production database URL (Render PostgreSQL)
- Test with production Pinecone index
- Verify all connections work
- Test server startup and health check

## Phase 8: Deployment & Verification

### 8.1 Deploy to Render

- Create Web Service on Render
- Connect GitHub repository
- Set build and start commands
- Configure all environment variables
- Deploy and monitor logs

### 8.2 Post-Deployment Tests

- Test health endpoint on Render URL
- Test document upload from frontend
- Verify CORS allows frontend domain
- Test authentication flow
- Monitor error logs
- Test database migrations ran successfully

### 8.3 Performance Testing

- Test concurrent document uploads
- Test database connection pooling under load
- Test Pinecone query performance
- Test S3 upload/download speeds
- Monitor resource usage on Render

## Testing Checklist

### Connection Tests

- [ ] PostgreSQL connection (local SQLite)
- [ ] PostgreSQL connection (Render)
- [ ] Pinecone index creation/connection
- [ ] Pinecone vector operations
- [ ] AWS S3 bucket access
- [ ] AWS S3 file operations
- [ ] FastAPI server startup
- [ ] FastAPI health endpoint

### Integration Tests

- [ ] Document upload → Database → S3 → Pinecone
- [ ] Document retrieval with presigned URL
- [ ] Document deletion (cascades)
- [ ] Training status calculation
- [ ] Authentication and authorization
- [ ] Error handling and logging

### Production Readiness

- [ ] All environment variables configured
- [ ] Database migrations applied
- [ ] Pinecone indexes created
- [ ] S3 bucket accessible
- [ ] Render deployment successful
- [ ] CORS configured correctly
- [ ] Logging working
- [ ] Error handling tested

## Files to Create/Modify

### New Test Files

- `tests/test_connections.py` - Connection tests for all services
- `scripts/test_postgres.py` - PostgreSQL-specific tests
- `scripts/test_pinecone.py` - Pinecone-specific tests
- `scripts/test_s3.py` - S3-specific tests
- `scripts/test_fastapi.py` - FastAPI server tests
- `scripts/test_e2e_document_upload.py` - End-to-end document flow
- `scripts/test_e2e_training.py` - End-to-end training flow
- `scripts/test_e2e_auth.py` - End-to-end auth flow

### Configuration Files

- `.env.local` - Local environment variables (create from template)
- `render.yaml` - Render infrastructure config (optional)
- Update `.gitignore` to exclude `.env.local`

### Migration Files

- `alembic/versions/001_initial.py` - Initial database schema

## Key Implementation Details

### Database Connection

- Use SQLAlchemy connection pooling
- Test both SQLite (local) and PostgreSQL (Render)
- Verify UUID types work correctly
- Test transaction handling

### Pinecone Configuration

- Index dimensions: 3072 (text-embedding-3-large)
- Metric: cosine
- Serverless tier
- Separate dev/prod indexes

### S3 Configuration

- Bucket: `youtopia-mind-data` (or custom)
- Region: `us-east-1` (or chosen region)
- File structure: `documents/{user_id}/{document_id}/{filename}`
- Presigned URLs: 1 hour expiry

### Error Handling

- All connection failures should log clearly
- Provide helpful error messages
- Test timeout scenarios
- Test invalid credentials

## Next Steps After Testing

1. Document all connection strings and credentials securely
2. Set up monitoring/alerts for service health
3. Create runbook for common issues
4. Set up CI/CD for automated testing
5. Configure backup strategy for PostgreSQL
6. Set up S3 lifecycle policies if needed