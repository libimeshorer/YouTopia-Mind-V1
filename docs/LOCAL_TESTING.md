# Local Testing Setup

## Overview

This guide explains how to set up a local testing environment for the YouTopia Mind backend, including PostgreSQL database, migrations, and schema verification.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ with virtual environment
- All Python dependencies installed (`pip install -r requirements.txt`)

## Quick Start

1. **Start local PostgreSQL**:
   ```bash
   docker-compose up -d postgres
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.local .env
   # Edit .env with your actual credentials
   ```

3. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Verify schema**:
   ```bash
   python scripts/verify_schema.py
   ```

5. **Start backend**:
   ```bash
   uvicorn src.api.server:app --reload --port 8000
   ```

6. **Or use the automated script**:
   ```bash
   ./scripts/test_local.sh
   ```

## Detailed Setup

### 1. Docker Compose Setup

The `docker-compose.yml` file provides:
- **PostgreSQL 15**: Local database server on port 5432
- **pgAdmin 4**: Database management UI on port 5050

**Start services**:
```bash
docker-compose up -d
```

**Stop services**:
```bash
docker-compose down
```

**Reset database** (removes all data):
```bash
docker-compose down -v
docker-compose up -d
```

### 2. Environment Configuration

Create `.env.local` from the template and update with your credentials:

```bash
cp .env.local .env
```

**Required variables**:
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://youtopia:youtopia_dev@localhost:5432/youtopia_mind`)
- `CLERK_SECRET_KEY`: Your Clerk secret key
- `CLERK_FRONTEND_API`: Your Clerk frontend API URL
- `PINECONE_API_KEY`: Your Pinecone API key
- `OPENAI_API_KEY`: Your OpenAI API key
- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key

### 3. Database Migrations

**Run migrations**:
```bash
alembic upgrade head
```

**Check migration status**:
```bash
alembic current
```

**Rollback last migration** (if needed):
```bash
alembic downgrade -1
```

**Create new migration** (after model changes):
```bash
alembic revision --autogenerate -m "description"
```

### 4. Schema Verification

The `verify_schema.py` script checks:
- All required tables exist
- All required columns exist
- Primary keys are correct
- ENUMs are created
- No deprecated columns (like `user_id`)

**Run verification**:
```bash
python scripts/verify_schema.py
```

**Expected output**:
```
✓ Table 'tenants' exists
  ✓ Column 'id' exists
  ✓ Column 'name' exists
  ...
✓✓✓ ALL SCHEMA CHECKS PASSED ✓✓✓
```

### 5. Testing Workflow

**Before every production deploy**:

1. **Reset local database** (fresh start):
   ```bash
   docker-compose down -v
   docker-compose up -d
   sleep 5
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Verify schema**:
   ```bash
   python scripts/verify_schema.py
   ```

4. **Start backend**:
   ```bash
   uvicorn src.api.server:app --reload
   ```

5. **Test endpoints**:
   ```bash
   curl http://localhost:8000/health
   ```

6. **If all tests pass, deploy to production**

## Database Management

### Access PostgreSQL CLI

```bash
docker-compose exec postgres psql -U youtopia -d youtopia_mind
```

### View Tables

```sql
\dt
```

### View Table Schema

```sql
\d table_name
```

### View ENUMs

```sql
SELECT typname FROM pg_type WHERE typtype = 'e';
```

### Reset Database

```bash
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

## pgAdmin Access

1. Open http://localhost:5050
2. Login:
   - Email: `admin@youtopia.local`
   - Password: `admin`
3. Add server:
   - Name: `Local PostgreSQL`
   - Host: `postgres` (container name)
   - Port: `5432`
   - Username: `youtopia`
   - Password: `youtopia_dev`
   - Database: `youtopia_mind`

## Troubleshooting

### PostgreSQL not starting

```bash
# Check logs
docker-compose logs postgres

# Check if port 5432 is already in use
lsof -i :5432
```

### Migration errors

```bash
# Check current migration state
alembic current

# Check migration history
alembic history

# If stuck, manually reset
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

### Schema verification fails

1. Check which checks failed
2. Compare with `src/database/models.py`
3. Ensure migration ran successfully
4. Check for deprecated columns that need removal

### Connection refused

- Ensure PostgreSQL container is running: `docker-compose ps`
- Check DATABASE_URL in `.env` matches docker-compose settings
- Wait a few seconds after starting container (PostgreSQL needs time to initialize)

## Best Practices

1. **Always test migrations locally** before deploying to production
2. **Use schema verification** to catch issues early
3. **Reset database** when testing major schema changes
4. **Keep .env.local** with dev credentials (never commit to git)
5. **Use docker-compose** for consistent local environment

## Next Steps

After local testing passes:
1. Commit changes
2. Push to repository
3. Deploy to production
4. Run migrations on production database
5. Verify production schema
