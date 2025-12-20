#!/bin/bash
# Reset Render PostgreSQL database and run migrations
# USE WITH CAUTION: This drops all data!

set -e

echo "🔍 Checking for DATABASE_URL..."

if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL not set"
    echo "Please set it from your Render dashboard:"
    echo "  export DATABASE_URL='your-render-postgres-url'"
    exit 1
fi

echo "⚠️  WARNING: This will DELETE ALL DATA in the database!"
echo "Database: $DATABASE_URL"
echo ""
read -p "Are you absolutely sure? Type 'yes' to continue: " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Aborted"
    exit 0
fi

echo ""
echo "🗑️  Dropping and recreating schema..."

psql "$DATABASE_URL" << EOF
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
EOF

echo "✅ Schema reset complete!"
echo ""
echo "📝 Now run migrations locally or redeploy on Render:"
echo "   alembic upgrade head"
echo ""
echo "   Or push to trigger Render deployment"
