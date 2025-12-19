# Development Environment Quick Start

This guide helps you set up and run the development environment locally.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (local or Render dev instance)
- Git

## Initial Setup (One-Time)

### 1. Clone and Install

```bash
cd /home/user/YouTopia-Mind-V1

# Install Python dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Set Up Environment Variables

```bash
# Create development environment file
cp .env.example .dev.env

# Edit .dev.env and fill in your development credentials:
# - ENVIRONMENT=development
# - CLERK_SECRET_KEY (from Clerk dev instance)
# - OPENAI_API_KEY
# - PINECONE_API_KEY
# - PINECONE_INDEX_NAME=youtopia-dev
# - S3_BUCKET_NAME=youtopia-s3-dev
# - DATABASE_URL (your dev database)

# Create frontend environment file
cp frontend/.env.example frontend/.env.local

# Edit frontend/.env.local:
# - VITE_API_URL=http://localhost:8000
# - VITE_CLERK_PUBLISHABLE_KEY (from Clerk dev instance)
```

### 3. Set Up Database

```bash
# Set environment
export ENVIRONMENT=development

# Run migrations
alembic upgrade head

# Verify connection
python scripts/test_postgres_connection.py
```

### 4. Verify Environment

```bash
# Check all environment configuration
python scripts/check_environment.py

# Expected output:
# ✓ Environment: development
# ✓ Pinecone Index: youtopia-dev
# ✓ S3 Bucket: youtopia-s3-dev
# ✓ Database: Connected
```

## Daily Development Workflow

### Starting the Dev Environment

You need **TWO terminals**:

#### Terminal 1: Backend API
```bash
cd /home/user/YouTopia-Mind-V1
source venv/bin/activate
export ENVIRONMENT=development

# Run backend server
uvicorn src.api.server:app --reload --port 8000

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Environment: development
# INFO:     Pinecone Index: youtopia-dev
# INFO:     S3 Bucket: youtopia-s3-dev
```

#### Terminal 2: Frontend
```bash
cd /home/user/YouTopia-Mind-V1/frontend
npm run dev

# Expected output:
# VITE v5.x.x  ready in xxx ms
# ➜  Local:   http://localhost:5173/
# ➜  Network: use --host to expose
```

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (FastAPI Swagger UI)
- **Health Check**: http://localhost:8000/health

## Common Development Tasks

### Running Tests

```bash
# Backend tests
export ENVIRONMENT=development
pytest

# Test specific components
python scripts/test_pinecone.py
python scripts/test_postgres_connection.py
python scripts/test_s3_functionality.py
```

### Database Operations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

### Ingesting Test Data

```bash
export ENVIRONMENT=development

# Ingest documents
python scripts/ingest_data.py --documents path/to/test.pdf

# The system will confirm you're in development mode
```

### Checking Environment Configuration

```bash
# Quick environment check
python scripts/check_environment.py

# View current settings
python -c "from src.config.settings import settings; print(f'Env: {settings.environment}'); print(f'Pinecone: {settings.pinecone_index_name}'); print(f'S3: {settings.s3_bucket_name}')"
```

## Troubleshooting

### Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'X'`
**Fix**:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Error**: `Database connection failed`
**Fix**: Check `DATABASE_URL` in `.dev.env` and ensure PostgreSQL is running

**Error**: `Pinecone index not found`
**Fix**: Create the index in Pinecone dashboard or check `PINECONE_INDEX_NAME` matches

### Frontend Won't Start

**Error**: `Cannot find module 'X'`
**Fix**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Error**: `VITE_CLERK_PUBLISHABLE_KEY is not set`
**Fix**: Create `frontend/.env.local` and add your Clerk publishable key

### Frontend Can't Connect to Backend

**Error**: `Failed to connect to backend at http://localhost:8000`

**Fix**:
1. Check backend is running (Terminal 1)
2. Check `VITE_API_URL` in `frontend/.env.local` is `http://localhost:8000`
3. Check CORS is allowing localhost in `src/api/server.py`
4. Test backend directly: `curl http://localhost:8000/health`

### Authentication Issues

**Error**: `Clerk authentication will not work`
**Fix**:
1. Check `VITE_CLERK_PUBLISHABLE_KEY` in `frontend/.env.local`
2. Check `CLERK_SECRET_KEY` in `.dev.env`
3. Ensure using development Clerk instance (pk_test_..., sk_test_...)
4. Verify Clerk dashboard has correct allowed origins (http://localhost:5173)

### Environment Not Detected

**Error**: System defaulting to wrong environment

**Fix**:
```bash
# Set explicitly
export ENVIRONMENT=development

# Or add to your shell profile (~/.bashrc, ~/.zshrc)
echo 'export ENVIRONMENT=development' >> ~/.bashrc
source ~/.bashrc

# Verify
python -c "import os; print(os.getenv('ENVIRONMENT'))"
```

## Best Practices

### Always Use Development Environment

```bash
# ALWAYS set this before running any scripts
export ENVIRONMENT=development

# Add to your shell profile to make permanent
echo 'export ENVIRONMENT=development' >> ~/.bashrc
```

### Never Use Production Resources in Dev

- ❌ Don't use `youtopia-prod` Pinecone index
- ❌ Don't use `youtopia-s3-prod` S3 bucket
- ❌ Don't use production PostgreSQL database
- ❌ Don't use production Clerk instance (sk_live_...)
- ✅ Always use separate dev resources

### Keep Dependencies Updated

```bash
# Backend
pip install -r requirements.txt --upgrade

# Frontend
cd frontend
npm update
```

### Clean Up Test Data

```bash
# Development is safe to reset
export ENVIRONMENT=development

# Note: reset() is blocked in production for safety
# In development, you can safely reset your vector store if needed
```

## Quick Reference

### Environment Variables

| Variable | Development | Production |
|----------|-------------|------------|
| `ENVIRONMENT` | `development` | `production` |
| `PINECONE_INDEX_NAME` | `youtopia-dev` | `youtopia-prod` |
| `S3_BUCKET_NAME` | `youtopia-s3-dev` | `youtopia-s3-prod` |
| `CLERK_SECRET_KEY` | `sk_test_...` | `sk_live_...` |
| `VITE_CLERK_PUBLISHABLE_KEY` | `pk_test_...` | `pk_live_...` |
| `VITE_API_URL` | `http://localhost:8000` | `https://api.you-topia.ai` |

### Useful Commands

```bash
# Start backend (development)
uvicorn src.api.server:app --reload --port 8000

# Start frontend (development)
cd frontend && npm run dev

# Run environment check
python scripts/check_environment.py

# Run migrations
alembic upgrade head

# Run tests
pytest
```

### Port Reference

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| Frontend Dev | 5173 | http://localhost:5173 |
| Frontend Preview | 4173 | http://localhost:4173 |
| PostgreSQL | 5432 | localhost:5432 |

---

**Need Help?**
- Check `docs/ENVIRONMENT_SETUP.md` for detailed environment configuration
- Check `docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md` before deploying
- Check API docs at http://localhost:8000/docs when backend is running
