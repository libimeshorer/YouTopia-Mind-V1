# Check Recent Data Script

This script helps you verify that data is being added to your PostgreSQL database correctly by showing the latest rows from each table.

## Features

- 📊 Shows the latest 10 rows (configurable) from each table
- 📈 Displays total row count and recent additions (last 24h)
- 🔒 Automatically masks sensitive data (passwords, tokens, credentials)
- ⏰ Orders by `created_at`, `updated_at`, or `id` (whichever is available)
- 🎯 Can check all tables or a specific table

## Usage

### Check All Tables

```bash
# Show latest 10 rows from all tables
python scripts/check_recent_data.py

# Show latest 20 rows from all tables
python scripts/check_recent_data.py --limit 20
```

### Check Specific Table

```bash
# Check only the clones table
python scripts/check_recent_data.py --table clones

# Check messages table with 5 latest rows
python scripts/check_recent_data.py --table messages --limit 5
```

## Available Tables

- `tenants` - Organizations/companies
- `clones` - Individual AI clones within organizations
- `sessions` - Conversation sessions
- `messages` - Individual messages in conversations
- `documents` - Uploaded training documents
- `insights` - User-provided insights (text/voice)
- `training_status` - Clone training progress
- `integrations` - Third-party service connections
- `data_sources` - Specific data sources within integrations

## Example Output

```
================================================================================
🔍 POSTGRESQL DATABASE - RECENT DATA CHECK
================================================================================
📅 Timestamp: 2024-01-15 10:30:45 UTC
📊 Showing latest 10 rows per table

================================================================================
📊 TABLE: clones
================================================================================
  📈 Total rows: 5
  🕐 Added in last 24h: 2

  Latest 5 rows:

  Row 1:
    id                   : 123e4567-e89b-12d3-a456-426614174000
    tenant_id            : 987fcdeb-51d3-12d3-a456-426614174000
    clerk_user_id        : user_2abc****
    first_name           : John
    last_name            : Doe
    email                : john****
    status               : active
    created_at           : 2024-01-15 09:30:00
    updated_at           : 2024-01-15 09:30:00
```

## Integration with Development Workflow

Use this script to:

1. **Verify API endpoints** - After creating data via API, check it was saved
2. **Debug issues** - See exactly what data exists in the database
3. **Monitor data flow** - Check if background jobs are adding data
4. **Test integrations** - Verify third-party data is being synced

## Environment

The script uses your configured `DATABASE_URL` from environment variables. Make sure you have the correct environment file loaded:

- Development: `.dev.env`
- Production: `.prod.env`
- Local overrides: `.env.local`

## Safety Features

- ✅ Read-only operations (no data modification)
- 🔒 Sensitive fields automatically masked
- 📊 Handles missing tables gracefully
- ⚠️ Shows errors without crashing

## Related Scripts

- `test_postgres_connection.py` - Test database connectivity
- `inspect_postgres_schema.py` - View complete schema structure
- `verify_schema.py` - Validate schema matches models
- `reset_render_db.py` - Reset database (development only)
