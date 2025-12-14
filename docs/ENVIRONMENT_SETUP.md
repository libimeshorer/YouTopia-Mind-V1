# Environment Setup Guide

This document describes the two-environment setup (development and production) for YouTopia Mind, including safety guidelines and best practices.

## Overview

YouTopia Mind uses a two-environment architecture:
- **Development (dev)**: For local development, testing, and experimentation
- **Production (prod)**: For customer-facing operations with real data

Each environment has separate instances of all backend resources:
- Pinecone indexes (e.g., `youtopia-dev` vs `youtopia-prod`)
- S3 buckets (e.g., `youtopia-s3-dev` vs `youtopia-s3-prod`)
- PostgreSQL databases (separate Render instances)
- Environment variables and configuration

## Safety Principles

1. **Fail Safe**: Defaults to development when `ENVIRONMENT` is unset
2. **Explicit Confirmation**: Production operations require explicit user confirmation
3. **Clear Logging**: Environment and resources are logged at startup
4. **Validation**: Resource names are validated to match environment
5. **Guards**: Destructive operations are blocked in production

## Environment Variables

### Core Environment Variable

The primary environment variable that controls the active environment:

```bash
ENVIRONMENT=development  # or "dev"
# or
ENVIRONMENT=production   # or "prod"
```

**Critical Safety**: If `ENVIRONMENT` is not set, the system **defaults to development** for safety.

### Environment Files

The system loads environment variables from files in this priority order:

1. `.env.local` (highest priority - local overrides)
2. `.dev.env` or `.prod.env` (based on `ENVIRONMENT` variable)
3. `.env` (fallback)

### Required Environment Variables

#### Development (`.dev.env`)

```bash
ENVIRONMENT=development

# Pinecone
PINECONE_API_KEY=your-dev-api-key
PINECONE_INDEX_NAME=youtopia-dev

# AWS S3
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-dev-access-key
AWS_SECRET_ACCESS_KEY=your-dev-secret-key
S3_BUCKET_NAME=youtopia-s3-dev
# or use separate variables:
S3_BUCKET_NAME_DEV=youtopia-s3-dev

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/youtopia_dev
# or use Render dev database URL

# OpenAI
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Clerk (for API server)
CLERK_SECRET_KEY=your-clerk-dev-key
```

#### Production (`.prod.env`)

```bash
ENVIRONMENT=production

# Pinecone
PINECONE_API_KEY=your-prod-api-key
PINECONE_INDEX_NAME=youtopia-prod

# AWS S3
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-prod-access-key
AWS_SECRET_ACCESS_KEY=your-prod-secret-key
S3_BUCKET_NAME=youtopia-s3-prod
# or use separate variables:
S3_BUCKET_NAME_PROD=youtopia-s3-prod

# Database
DATABASE_URL=postgresql://user:pass@prod-db.render.com:5432/youtopia_prod
# Use Render production database URL

# OpenAI
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Clerk (for API server)
CLERK_SECRET_KEY=your-clerk-prod-key
```

## Resource Naming Conventions

To ensure safety and clarity, resources should follow naming conventions that match the environment:

### Pinecone Indexes
- Development: `youtopia-dev` (must contain "dev")
- Production: `youtopia-prod` (must contain "prod")

### S3 Buckets
- Development: `youtopia-s3-dev` (must contain "dev")
- Production: `youtopia-s3-prod` (must contain "prod")

### Database URLs
- Development: May use `localhost` or Render dev database
- Production: Must use remote database (Render production), not `localhost`

The system validates these conventions and warns if resource names don't match the environment.

## Setting Up Environments

### Initial Setup

1. **Create environment files**:
   ```bash
   # Development
   cp .env.example .dev.env
   # Edit .dev.env with dev credentials
   
   # Production
   cp .env.example .prod.env
   # Edit .prod.env with prod credentials
   ```

2. **Set environment variable**:
   ```bash
   # For development
   export ENVIRONMENT=development
   # or
   export ENVIRONMENT=dev
   
   # For production (be careful!)
   export ENVIRONMENT=production
   # or
   export ENVIRONMENT=prod
   ```

3. **Verify configuration**:
   ```bash
   python scripts/check_environment.py
   ```

### Local Development Setup

For local development, create `.env.local` for overrides:

```bash
# .env.local (for local development)
ENVIRONMENT=development
# Add any local overrides here
```

## Safety Features

### Automatic Environment Validation

The system automatically:
- Validates that resource names match the environment
- Logs environment and resources at startup
- Warns when production is detected
- Blocks destructive operations in production

### Production Guards

The following operations are **blocked in production**:

- `PineconeStore.reset()` - Index deletion and recreation
- Other destructive operations may require explicit confirmation

### Production Warnings

When running in production, you'll see:
- Startup warnings in logs
- Prominent console warnings
- Requests for confirmation before ingestion operations
- Warnings for delete operations without namespace isolation

## Running Operations

### Development Mode

```bash
# Set environment
export ENVIRONMENT=development

# Run ingestion
python scripts/ingest_data.py --documents file1.pdf file2.pdf

# Run tests
python scripts/test_pinecone.py
python scripts/test_postgres_connection.py
```

### Production Mode

```bash
# Set environment (carefully!)
export ENVIRONMENT=production

# Verify environment first
python scripts/check_environment.py

# Production operations will require confirmation
python scripts/ingest_data.py --documents file1.pdf
# You'll be prompted: "Continue with production ingestion? (type 'yes' to confirm)"
```

## Testing

### Development Tests

Most test scripts default to development mode:

```bash
# These default to development if ENVIRONMENT is unset
python scripts/test_pinecone.py
python scripts/test_postgres_connection.py
python scripts/test_s3_functionality.py
```

### Production-Safe Tests

Some tests are designed to run safely in production:

```bash
# Production-safe health check (uses isolated test namespace)
python scripts/test_pinecone_prod_safe.py
```

## Troubleshooting

### Environment Not Detected

If the system isn't detecting your environment:

1. Check that `ENVIRONMENT` is set:
   ```bash
   echo $ENVIRONMENT
   ```

2. Verify environment files exist:
   ```bash
   ls -la .dev.env .prod.env
   ```

3. Check environment loading in logs (look for "Environment Configuration" log)

### Resource Name Mismatches

If you see warnings about resource name mismatches:

1. Check resource names match environment conventions
2. Verify `PINECONE_INDEX_NAME` contains "dev" or "prod" appropriately
3. Verify `S3_BUCKET_NAME` contains "dev" or "prod" appropriately

### Accidental Production Operations

If you accidentally try to run a production operation:

1. The system will block destructive operations (e.g., `reset()`)
2. Ingestion scripts require explicit confirmation
3. Always check logs for environment warnings

### Default to Production Issue

If the system defaults to production (shouldn't happen with current code):

1. Check `ENVIRONMENT` variable is set correctly
2. Ensure environment files are configured
3. Review `src/config/settings.py` - it should default to development

## Best Practices

1. **Always verify environment before operations**:
   ```bash
   python scripts/check_environment.py
   ```

2. **Use development for testing**: Never test new code or scripts in production

3. **Check logs at startup**: Look for environment configuration logs

4. **Separate credentials**: Use different API keys and credentials for dev/prod

5. **Version control**: Never commit `.env.local`, `.dev.env`, or `.prod.env` to git (they're in `.gitignore`)

6. **Documentation**: Document any custom environment setups

7. **Team communication**: Communicate when switching between environments

## CI/CD Integration

When setting up CI/CD (future):

1. Set `ENVIRONMENT` in CI/CD environment variables
2. Use separate secrets for dev/staging/production
3. Never run destructive tests in production pipelines
4. Add environment validation as a CI/CD step

## Additional Resources

- [Production Checklist](./PRODUCTION_CHECKLIST.md) - Pre-deployment checklist
- [Backend Architecture](../reference/BACKEND_ARCHITECTURE.md) - System architecture
- `scripts/check_environment.py` - Environment validation script
