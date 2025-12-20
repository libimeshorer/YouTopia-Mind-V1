#!/usr/bin/env python3
"""
Reset Render PostgreSQL database and prepare for migrations.
USE WITH CAUTION: This drops all data!
"""
import os
import sys
import psycopg2
from urllib.parse import urlparse


def reset_database(database_url: str):
    """Drop and recreate the public schema."""
    print("🗑️  Dropping and recreating schema...")

    # Parse the database URL to show sanitized version
    parsed = urlparse(database_url)
    safe_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}"
    print(f"Database: {safe_url}")

    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()

        # Drop and recreate schema
        cursor.execute("DROP SCHEMA public CASCADE;")
        cursor.execute("CREATE SCHEMA public;")
        cursor.execute("GRANT ALL ON SCHEMA public TO postgres;")
        cursor.execute("GRANT ALL ON SCHEMA public TO public;")

        cursor.close()
        conn.close()

        print("✅ Schema reset complete!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("🔍 Checking for DATABASE_URL...")

    # Get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        print("\nPlease set it from your Render dashboard:")
        print("  export DATABASE_URL='your-render-postgres-url'")
        print("\nOr run with:")
        print("  DATABASE_URL='your-url' python scripts/reset_render_db.py")
        sys.exit(1)

    # Warning and confirmation
    print("\n⚠️  WARNING: This will DELETE ALL DATA in the database!")
    print("Database URL is set")
    print("")

    confirm = input("Are you absolutely sure? Type 'yes' to continue: ")

    if confirm.lower() != 'yes':
        print("❌ Aborted")
        sys.exit(0)

    print("")

    # Reset the database
    if reset_database(database_url):
        print("")
        print("📝 Next steps:")
        print("   1. Run migrations: alembic upgrade head")
        print("   2. Or push to trigger Render deployment")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
