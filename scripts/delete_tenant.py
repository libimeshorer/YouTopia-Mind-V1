#!/usr/bin/env python3
"""Script to view and delete specific tenant from the database"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import create_engine, text
    from src.config.settings import settings
    from src.database.db import Base, engine, get_db
    from src.database.models import Tenant, Clone
except ImportError as e:
    print(f"❌ Error importing dependencies: {e}")
    print("\nPlease install dependencies first:")
    print("  pip install -r requirements.txt")
    sys.exit(1)


def list_tenants():
    """List all tenants with their associated clones"""
    print("\n" + "="*120)
    print("TENANTS IN DATABASE")
    print("="*120)

    db = next(get_db())

    result = db.execute(text("""
        SELECT
            t.id,
            t.name,
            t.clerk_org_id,
            t.created_at,
            COUNT(c.id) as clone_count,
            STRING_AGG(c.clerk_user_id, ', ') as clone_users
        FROM tenants t
        LEFT JOIN clones c ON c.tenant_id = t.id
        GROUP BY t.id, t.name, t.clerk_org_id, t.created_at
        ORDER BY t.created_at DESC
    """)).fetchall()

    if not result:
        print("No tenants found in database.")
        return []

    print(f"\n{'#':<4} {'Tenant ID':<38} {'Clones':<7} {'Created At':<20} {'Name':<30}")
    print("-" * 120)

    tenants = []
    for idx, row in enumerate(result, 1):
        tenant_id = str(row[0])
        name = str(row[1])[:30]
        created = str(row[3])[:19]
        clone_count = row[4]

        print(f"{idx:<4} {tenant_id:<38} {clone_count:<7} {created:<20} {name:<30}")
        tenants.append(tenant_id)

    print("="*120)
    return tenants


def delete_tenant(tenant_id: str):
    """Delete a specific tenant by ID"""
    db = next(get_db())

    # First check if tenant exists
    result = db.execute(
        text("SELECT id, name FROM tenants WHERE id = :tenant_id"),
        {"tenant_id": tenant_id}
    ).fetchone()

    if not result:
        print(f"❌ Tenant with ID {tenant_id} not found.")
        return False

    tenant_name = result[1]

    # Confirm deletion
    print(f"\n⚠️  You are about to delete:")
    print(f"   Tenant ID: {tenant_id}")
    print(f"   Name: {tenant_name}")
    print(f"\n   This will CASCADE delete all associated clones and their data!")

    confirm = input("\nType 'DELETE' to confirm: ").strip()

    if confirm != "DELETE":
        print("❌ Deletion cancelled.")
        return False

    try:
        # Delete the tenant (CASCADE will handle related records)
        db.execute(
            text("DELETE FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        db.commit()
        print(f"✅ Tenant {tenant_id} deleted successfully!")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting tenant: {e}")
        return False


def main():
    """Main function"""
    print("\n🔍 Tenant Management Tool")

    # List all tenants
    tenants = list_tenants()

    if not tenants:
        return

    print("\n" + "="*120)
    print("DELETE TENANT")
    print("="*120)
    print("\nOptions:")
    print("  1. Enter tenant ID to delete")
    print("  2. Enter row number (1, 2, 3, etc.)")
    print("  3. Press Enter to exit")

    choice = input("\nYour choice: ").strip()

    if not choice:
        print("Exiting...")
        return

    # Check if it's a number (row selection)
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(tenants):
            tenant_id = tenants[idx]
        else:
            print(f"❌ Invalid row number. Must be between 1 and {len(tenants)}")
            return
    else:
        # Assume it's a UUID
        tenant_id = choice

    delete_tenant(tenant_id)


if __name__ == "__main__":
    main()
