#!/bin/bash
# Render startup script - runs migrations then starts the server

set -e  # Exit on any error

echo "🔄 Running database migrations..."

# Set environment variables for the migration
export ALLOW_DESTRUCTIVE_MIGRATIONS=${ALLOW_DESTRUCTIVE_MIGRATIONS:-false}

# Run Alembic migrations
alembic upgrade head

echo "✅ Migrations complete!"
echo "🚀 Starting FastAPI server..."

# Start the FastAPI application
exec uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT:-8000}
