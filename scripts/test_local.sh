#!/bin/bash
set -e

echo "===================================="
echo "Local Testing Environment Setup"
echo "===================================="

# Start PostgreSQL
echo "1. Starting PostgreSQL..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "2. Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U youtopia > /dev/null 2>&1; do
  sleep 1
done
echo "   PostgreSQL is ready!"

# Run migrations
echo "3. Running database migrations..."
export ENVIRONMENT=development
alembic upgrade head

# Verify schema
echo "4. Verifying database schema..."
python scripts/verify_schema.py

if [ $? -ne 0 ]; then
    echo "❌ Schema verification failed!"
    exit 1
fi

echo ""
echo "✅ All checks passed!"
echo ""
echo "5. Starting backend server..."
echo "   Backend will be available at http://localhost:8000"
echo "   API documentation at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn src.api.server:app --reload --port 8000
