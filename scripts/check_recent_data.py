#!/usr/bin/env python3
"""
Script to check recent data in PostgreSQL tables.
Shows the latest 10 rows from each table to verify data is being added correctly.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from src.database.db import engine, SessionLocal
from src.database.models import (
    Tenant, Clone, Session as ChatSession, Message, Document,
    Insight, TrainingStatus, Integration, DataSource, ChunkScore
)


def mask_sensitive_data(value: str, show_chars: int = 4) -> str:
    """Mask sensitive string data, showing only first few characters."""
    if not value or len(value) <= show_chars:
        return "****"
    return f"{value[:show_chars]}****"


def format_value(value: Any, column_name: str) -> str:
    """Format value for display, masking sensitive data."""
    if value is None:
        return "NULL"

    # Mask sensitive fields
    sensitive_fields = ['password', 'token', 'secret', 'key', 'credentials', 'api_key']
    if any(field in column_name.lower() for field in sensitive_fields):
        if isinstance(value, str):
            return mask_sensitive_data(value)

    # Format timestamps
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')

    # Truncate long strings
    if isinstance(value, str) and len(value) > 50:
        return f"{value[:47]}..."

    # Handle dicts/JSON
    if isinstance(value, dict):
        return f"{{...{len(value)} keys}}"

    return str(value)


def get_latest_rows(db: Session, model, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the latest N rows from a table.
    Attempts to order by created_at, updated_at, or id as fallback.
    """
    try:
        # Get column names
        columns = [col.name for col in inspect(model).columns]

        # Determine order by column
        order_column = None
        if 'created_at' in columns:
            order_column = 'created_at'
        elif 'updated_at' in columns:
            order_column = 'updated_at'
        elif 'id' in columns:
            order_column = 'id'

        # Build query
        query = db.query(model)
        if order_column:
            query = query.order_by(getattr(model, order_column).desc())

        rows = query.limit(limit).all()

        # Convert to dictionaries
        result = []
        for row in rows:
            row_dict = {}
            for col in columns:
                row_dict[col] = getattr(row, col)
            result.append(row_dict)

        return result

    except Exception as e:
        print(f"  ❌ Error querying table: {e}")
        return []


def get_table_stats(db: Session, model) -> Dict[str, Any]:
    """Get basic statistics about a table."""
    try:
        total_count = db.query(model).count()

        # Check for records in last 24 hours if created_at exists
        columns = [col.name for col in inspect(model).columns]
        recent_count = None

        if 'created_at' in columns:
            from datetime import timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_count = db.query(model).filter(
                getattr(model, 'created_at') >= yesterday
            ).count()

        return {
            'total': total_count,
            'recent_24h': recent_count
        }
    except Exception as e:
        return {'error': str(e)}


def print_table_data(table_name: str, rows: List[Dict[str, Any]], stats: Dict[str, Any]):
    """Print table data in a formatted way."""
    print(f"\n{'=' * 80}")
    print(f"📊 TABLE: {table_name}")
    print(f"{'=' * 80}")

    # Print statistics
    if 'error' in stats:
        print(f"  ⚠️  Stats error: {stats['error']}")
    else:
        print(f"  📈 Total rows: {stats['total']}")
        if stats['recent_24h'] is not None:
            print(f"  🕐 Added in last 24h: {stats['recent_24h']}")

    if not rows:
        print("  📭 No data in this table")
        return

    print(f"\n  Latest {len(rows)} rows:")
    print(f"  {'-' * 76}")

    # Print each row
    for i, row in enumerate(rows, 1):
        print(f"\n  Row {i}:")
        for col_name, value in row.items():
            formatted_value = format_value(value, col_name)
            print(f"    {col_name:20} : {formatted_value}")


def check_all_tables(limit: int = 10):
    """Check all tables and display recent data."""

    print("\n" + "=" * 80)
    print("🔍 POSTGRESQL DATABASE - RECENT DATA CHECK")
    print("=" * 80)
    print(f"📅 Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"📊 Showing latest {limit} rows per table")

    # List of all models to check
    models = [
        ('tenants', Tenant),
        ('clones', Clone),
        ('sessions', ChatSession),
        ('messages', Message),
        ('documents', Document),
        ('insights', Insight),
        ('training_status', TrainingStatus),
        ('integrations', Integration),
        ('data_sources', DataSource),
        ('chunk_scores', ChunkScore),
    ]

    db = SessionLocal()
    try:
        for table_name, model in models:
            stats = get_table_stats(db, model)
            rows = get_latest_rows(db, model, limit)
            print_table_data(table_name, rows, stats)

        print(f"\n{'=' * 80}")
        print("✅ Check complete!")
        print(f"{'=' * 80}\n")

    except Exception as e:
        print(f"\n❌ Error during check: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def check_specific_table(table_name: str, limit: int = 10):
    """Check a specific table."""

    # Map table names to models
    table_map = {
        'tenants': Tenant,
        'clones': Clone,
        'sessions': ChatSession,
        'messages': Message,
        'documents': Document,
        'insights': Insight,
        'training_status': TrainingStatus,
        'integrations': Integration,
        'data_sources': DataSource,
        'chunk_scores': ChunkScore,
    }

    model = table_map.get(table_name.lower())
    if not model:
        print(f"❌ Unknown table: {table_name}")
        print(f"Available tables: {', '.join(table_map.keys())}")
        return

    print("\n" + "=" * 80)
    print("🔍 POSTGRESQL DATABASE - TABLE CHECK")
    print("=" * 80)
    print(f"📅 Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    db = SessionLocal()
    try:
        stats = get_table_stats(db, model)
        rows = get_latest_rows(db, model, limit)
        print_table_data(table_name, rows, stats)

        print(f"\n{'=' * 80}")
        print("✅ Check complete!")
        print(f"{'=' * 80}\n")

    except Exception as e:
        print(f"\n❌ Error during check: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Check recent data in PostgreSQL tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check all tables (10 latest rows each)
  python scripts/check_recent_data.py

  # Check all tables (20 latest rows each)
  python scripts/check_recent_data.py --limit 20

  # Check specific table
  python scripts/check_recent_data.py --table clones

  # Check specific table with custom limit
  python scripts/check_recent_data.py --table messages --limit 5

Available tables:
  tenants, clones, sessions, messages, documents, insights,
  training_status, integrations, data_sources
        """
    )

    parser.add_argument(
        '--table', '-t',
        type=str,
        help='Specific table to check (default: all tables)'
    )

    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=10,
        help='Number of latest rows to show (default: 10)'
    )

    args = parser.parse_args()

    try:
        if args.table:
            check_specific_table(args.table, args.limit)
        else:
            check_all_tables(args.limit)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
