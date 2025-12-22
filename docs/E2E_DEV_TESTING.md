# End-to-End Development Testing Guide

This guide explains how to test the full YouTopia Mind application flow in development mode, including authentication, database operations, and all backend services.

## Prerequisites

- Docker and Docker Compose installed
- Node.js and npm installed
- Python 3.11+ with virtual environment
- Clerk account (see options below)
- Render dev PostgreSQL database set up

## Environment Options

### Option 1: Separate Clerk Dev Application (RECOMMENDED)

**Best for:** Complete isolation between dev and production

#### Setup Steps:

1. **Create Clerk Dev Application:**
   - Go to https://clerk.com dashboard
   - Create new application: "YouTopia Mind - Dev"
   - Enable Email/Password and Google OAuth
   - Copy the publishable key (starts with `pk_test_...`)
   - Copy the secret key (starts with `sk_test_...`)

2. **Configure Frontend for Dev:**

   Create `frontend/.env.local`:
   ```bash
   VITE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_DEV_KEY_HERE
   ```

3. **Configure Backend for Dev:**

   Create or update `.dev.env` in project root:
   ```bash
   ENVIRONMENT=development

   # Database
   DATABASE_URL=postgresql://user:pass@dpg-xxxxx.render.com:5432/youtopia_dev

   # Clerk (Development)
   CLERK_SECRET_KEY=sk_test_YOUR_DEV_SECRET_KEY

   # Pinecone
   PINECONE_API_KEY=your-pinecone-key
   PINECONE_INDEX_NAME=youtopia-dev

   # AWS S3
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your-dev-access-key
   AWS_SECRET_ACCESS_KEY=your-dev-secret-key
   S3_BUCKET_NAME=youtopia-s3-dev

   # OpenAI
   OPENAI_API_KEY=your-openai-key
   OPENAI_MODEL=gpt-4-turbo-preview
   OPENAI_EMBEDDING_MODEL=text-embedding-3-large
   ```

#### Benefits:
- ✅ Complete isolation: dev users won't appear in production
- ✅ Can test authentication flows without affecting production
- ✅ Safe to experiment with Clerk settings
- ✅ Clear separation of concerns

---

### Option 2: Shared Clerk Instance (Quick Start)

**Best for:** Solo development, quick testing, or if you don't want to manage multiple Clerk apps

#### Setup Steps:

1. **Use Production Clerk Keys in Dev:**

   Create `frontend/.env.local`:
   ```bash
   VITE_CLERK_PUBLISHABLE_KEY=pk_live_YOUR_PROD_KEY  # or pk_test if still testing
   ```

2. **Configure Backend:**

   Create or update `.dev.env`:
   ```bash
   ENVIRONMENT=development
   DATABASE_URL=postgresql://user:pass@dpg-xxxxx.render.com:5432/youtopia_dev
   CLERK_SECRET_KEY=sk_live_YOUR_PROD_SECRET  # Same as production
   # ... rest of dev config (Pinecone, S3, etc.)
   ```

#### Trade-offs:
- ⚠️ Users created in dev will exist in production Clerk
- ⚠️ Authentication state is shared across environments
- ✅ Simpler setup - only one Clerk application to manage
- ✅ Works fine for solo development

---

## Running End-to-End Tests

### 1. Start PostgreSQL (if using local database)

If using local PostgreSQL instead of Render dev database:

```bash
docker-compose up -d postgres
sleep 5  # Wait for PostgreSQL to initialize
```

### 2. Run Database Migrations

```bash
# Make sure ENVIRONMENT is set to development
export ENVIRONMENT=development

# Run migrations
alembic upgrade head

# Verify schema
python scripts/verify_schema.py
```

Expected output:
```
✓ Table 'tenants' exists
✓ Table 'users' exists
✓ Table 'clones' exists
...
✓✓✓ ALL SCHEMA CHECKS PASSED ✓✓✓
```

### 3. Start Backend Server

```bash
# From project root
export ENVIRONMENT=development
uvicorn src.api.server:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Environment: development
INFO:     Database: Connected
```

Verify backend health:
```bash
curl http://localhost:8000/health
```

### 4. Start Frontend Development Server

```bash
# In a new terminal
cd frontend
npm run dev
```

You should see:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:8080/
➜  Network: use --host to expose
```

### 5. Test the Full Flow

#### Step 1: Sign Up (Create Account)

1. Open http://localhost:8080 in browser
2. Click "Sign In" button (top right)
3. Click "Sign up" at bottom
4. Create account with:
   - Email and password, OR
   - Google OAuth

**What happens:**
- User created in Clerk
- User profile stored in dev PostgreSQL database
- Session token issued

#### Step 2: Access Dashboard

1. After sign up, you'll be redirected to `/dashboard`
2. Verify you see the dashboard interface
3. Check that you're authenticated (user button in header)

**What happens:**
- Protected route checks authentication
- Dashboard loads user's clones from dev database
- Clerk session is active

#### Step 3: Create a Clone

1. In Dashboard, click "Create Clone"
2. Fill in clone details:
   - Name: "My Test Clone"
   - Description: "Testing end-to-end flow"
   - Personality: Choose one
3. Click "Create"

**What happens:**
- POST request to backend API
- Clone record created in dev PostgreSQL (`clones` table)
- Associated with your user account
- Tenant context maintained

#### Step 4: Upload Documents

1. Select your clone
2. Click "Upload Documents"
3. Choose PDF/text files
4. Upload

**What happens:**
- Files uploaded to S3 dev bucket (`youtopia-s3-dev`)
- Documents ingested and chunked
- Embeddings generated via OpenAI
- Vectors stored in Pinecone dev index (`youtopia-dev`)
- Document metadata stored in PostgreSQL

#### Step 5: Chat with Clone

1. Open chat interface
2. Send a message: "What do you know about [topic in your docs]?"
3. Verify response uses uploaded content

**What happens:**
- Query embedded via OpenAI
- Similar vectors retrieved from Pinecone dev index
- RAG pipeline assembles context
- LLM generates response using retrieved documents
- Chat history stored in database

#### Step 6: Verify Data in Database

```bash
# Connect to your dev database
# If using local PostgreSQL:
docker-compose exec postgres psql -U youtopia -d youtopia_mind

# If using Render dev database:
psql $DATABASE_URL

# Check data:
\dt                           # List tables
SELECT * FROM tenants;        # View tenants
SELECT * FROM users;          # View users (should see your account)
SELECT * FROM clones;         # View clones (should see your test clone)
SELECT * FROM documents;      # View uploaded documents
\q                            # Quit
```

---

## Verification Checklist

Use this checklist to verify your end-to-end setup:

### Backend Services
- [ ] PostgreSQL running and accessible
- [ ] Alembic migrations completed successfully
- [ ] Backend server starts without errors
- [ ] `/health` endpoint returns 200 OK
- [ ] Environment logs show "development" mode

### Frontend
- [ ] Frontend dev server running on port 8080
- [ ] Clerk publishable key loaded (check browser console)
- [ ] No authentication errors in console

### Authentication Flow
- [ ] Can access sign-up page
- [ ] Can create new account (email or OAuth)
- [ ] Redirected to dashboard after sign-up
- [ ] User button shows in header when authenticated
- [ ] Can sign out and sign back in

### Database Operations
- [ ] User record created in `users` table
- [ ] Tenant record created in `tenants` table
- [ ] Can create clone (record appears in `clones` table)
- [ ] Clone associated with correct user and tenant

### Document Upload & RAG
- [ ] Can upload documents through UI
- [ ] Files appear in S3 dev bucket
- [ ] Document records created in database
- [ ] Embeddings stored in Pinecone dev index
- [ ] Chat retrieves relevant context from uploaded docs

### Environment Isolation
- [ ] Using dev database (not production)
- [ ] Using dev Pinecone index (`youtopia-dev`)
- [ ] Using dev S3 bucket (`youtopia-s3-dev`)
- [ ] Backend logs show "ENVIRONMENT=development"

---

## Troubleshooting

### Clerk Authentication Issues

**Problem:** "Authentication is not configured" error

**Solutions:**
1. Check `frontend/.env.local` exists with `VITE_CLERK_PUBLISHABLE_KEY`
2. Restart frontend dev server (Vite needs restart after env changes)
3. Check browser console for Clerk config logs
4. Verify key format: `pk_test_...` or `pk_live_...`

### Database Connection Issues

**Problem:** "Could not connect to database"

**Solutions:**
1. Verify `DATABASE_URL` in `.dev.env`
2. Check database is running:
   - Local: `docker-compose ps`
   - Render: Check Render dashboard
3. Test connection: `python scripts/test_postgres_connection.py`
4. Check firewall/network access to Render database

### Migration Issues

**Problem:** Alembic migration fails

**Solutions:**
1. Check current migration: `alembic current`
2. Check migration history: `alembic history`
3. If stuck, reset local database:
   ```bash
   docker-compose down -v
   docker-compose up -d
   alembic upgrade head
   ```

### Backend API Errors

**Problem:** 500 errors when making API calls

**Solutions:**
1. Check backend logs for errors
2. Verify all environment variables are set
3. Test individual services:
   - Pinecone: `python scripts/test_pinecone.py`
   - S3: `python scripts/test_s3_functionality.py`
   - Database: `python scripts/test_postgres_connection.py`

### Document Upload Issues

**Problem:** Documents upload but not searchable

**Solutions:**
1. Check Pinecone dev index exists: `python scripts/test_pinecone.py`
2. Verify OpenAI API key is valid
3. Check S3 bucket permissions
4. Review backend logs during upload

---

## Environment Variables Reference

### Frontend (.env.local)

```bash
# Clerk Authentication
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxx  # or pk_live_xxx

# API URL (if needed)
VITE_API_URL=http://localhost:8000
```

### Backend (.dev.env)

```bash
# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Clerk
CLERK_SECRET_KEY=sk_test_xxx  # or sk_live_xxx

# Pinecone
PINECONE_API_KEY=xxx
PINECONE_INDEX_NAME=youtopia-dev

# AWS S3
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
S3_BUCKET_NAME=youtopia-s3-dev

# OpenAI
OPENAI_API_KEY=xxx
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Optional
LOG_LEVEL=INFO
```

---

## Next Steps After Successful E2E Testing

1. **Test all features:**
   - Create multiple clones
   - Upload various document types
   - Test chat with different queries
   - Verify user isolation (create second user, verify can't see first user's clones)

2. **Performance testing:**
   - Upload larger documents
   - Test concurrent users
   - Check response times

3. **Deploy to staging/production:**
   - Set `ENVIRONMENT=production` for production backend
   - Use production Clerk keys
   - Point to production database, Pinecone, S3

4. **Set up monitoring:**
   - Application logs
   - Error tracking
   - Performance metrics

---

## Best Practices

1. **Always verify environment before testing:**
   ```bash
   python scripts/check_environment.py
   ```

2. **Keep dev and prod separate:**
   - Never test in production
   - Use separate credentials for all services
   - Verify environment logs on startup

3. **Clean up test data:**
   - Periodically clean up dev database
   - Remove test documents from S3 dev bucket
   - Monitor Pinecone dev index usage

4. **Document your setup:**
   - Keep `.env.example` files updated
   - Document any custom configuration
   - Share setup with team members

---

## Quick Reference Commands

```bash
# Check environment
python scripts/check_environment.py

# Start local PostgreSQL
docker-compose up -d postgres

# Run migrations
export ENVIRONMENT=development
alembic upgrade head

# Verify schema
python scripts/verify_schema.py

# Start backend
uvicorn src.api.server:app --reload --port 8000

# Start frontend
cd frontend && npm run dev

# Test database connection
python scripts/test_postgres_connection.py

# Test Pinecone
python scripts/test_pinecone.py

# View logs
docker-compose logs -f postgres  # PostgreSQL logs
```

---

## Additional Resources

- [Environment Setup Guide](./ENVIRONMENT_SETUP.md)
- [Local Testing Guide](./LOCAL_TESTING.md)
- [Clerk Setup Guide](../frontend/CLERK_SETUP.md)
- [Production Checklist](./PRODUCTION_CHECKLIST.md)
