# Scripts Setup Guide

This directory contains database maintenance and inspection scripts for the YouTopia Mind project.

## Installation

Before running any scripts, ensure you have Python dependencies installed:

```bash
# Install all dependencies
pip install -r requirements.txt

# Or if using a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Configuration

Scripts use your DATABASE_URL from environment variables. Ensure you have the correct `.env` file:

```bash
# Development (default)
cp .dev.env .env

# Or for production
cp .prod.env .env

# Or create local overrides
cp .env.local.example .env.local
```

## Available Scripts

### 1. Check Recent Data (NEW!)

**Purpose:** Verify data is being added correctly by viewing latest rows

```bash
# Check all tables
python scripts/check_recent_data.py

# Check specific table
python scripts/check_recent_data.py --table clones --limit 20
```

See [README_CHECK_DATA.md](README_CHECK_DATA.md) for detailed usage.

### 2. Test PostgreSQL Connection

**Purpose:** Verify database connectivity and basic operations

```bash
python scripts/test_postgres_connection.py
```

### 3. Inspect Schema

**Purpose:** View complete database schema structure

```bash
python scripts/inspect_postgres_schema.py
```

### 4. Verify Schema

**Purpose:** Validate database schema matches model definitions

```bash
python scripts/verify_schema.py
```

### 5. Reset Database (⚠️ Development Only)

**Purpose:** Drop and recreate all tables (fresh start)

```bash
python scripts/reset_render_db.py
```

**WARNING:** This will delete all data! Only use in development.

## Quick Start

After installing dependencies:

```bash
# 1. Test connection
python scripts/test_postgres_connection.py

# 2. Verify schema
python scripts/verify_schema.py

# 3. Check your data
python scripts/check_recent_data.py --limit 5
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'sqlalchemy'"

Install dependencies: `pip install -r requirements.txt`

### "No password supplied" or connection errors

Check your `.env` file has the correct `DATABASE_URL`:
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

### "relation does not exist" errors

Run migrations to create tables:
```bash
alembic upgrade head
```

## Security Notes

- ✅ Scripts automatically mask sensitive data (passwords, tokens)
- ✅ All scripts are read-only except `reset_render_db.py`
- ⚠️ Never commit `.env` files with real credentials
- ⚠️ Be careful running reset script in production (it has safeguards)
