#!/usr/bin/env python3
"""
Detailed PostgreSQL schema inspector for Render database.
Shows comprehensive schema information including tables, columns, types, constraints, and indexes.
"""
import os
import sys
import psycopg2
from urllib.parse import urlparse
from typing import Dict, List


def get_all_tables(cursor) -> List[str]:
    """Get all tables in the public schema."""
    cursor.execute("""
        SELECT tablename
        FROM pg_catalog.pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """)
    return [row[0] for row in cursor.fetchall()]


def get_table_columns(cursor, table_name: str) -> List[Dict]:
    """Get detailed column information for a table."""
    cursor.execute(f"""
        SELECT
            column_name,
            data_type,
            udt_name,
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = '{table_name}'
        ORDER BY ordinal_position;
    """)

    columns = []
    for row in cursor.fetchall():
        columns.append({
            'name': row[0],
            'type': row[1],
            'udt_name': row[2],
            'max_length': row[3],
            'nullable': row[4],
            'default': row[5]
        })
    return columns


def get_primary_key(cursor, table_name: str) -> List[str]:
    """Get primary key columns for a table."""
    cursor.execute(f"""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = '{table_name}'::regclass
        AND i.indisprimary
        ORDER BY a.attnum;
    """)
    return [row[0] for row in cursor.fetchall()]


def get_foreign_keys(cursor, table_name: str) -> List[Dict]:
    """Get foreign key constraints for a table."""
    cursor.execute(f"""
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints AS rc
            ON rc.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = '{table_name}'
        AND tc.table_schema = 'public';
    """)

    fks = []
    for row in cursor.fetchall():
        fks.append({
            'column': row[0],
            'references_table': row[1],
            'references_column': row[2],
            'on_delete': row[3]
        })
    return fks


def get_indexes(cursor, table_name: str) -> List[Dict]:
    """Get indexes for a table."""
    cursor.execute(f"""
        SELECT
            i.relname AS index_name,
            a.attname AS column_name,
            ix.indisunique AS is_unique,
            ix.indisprimary AS is_primary
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        WHERE t.relkind = 'r'
        AND t.relname = '{table_name}'
        AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        ORDER BY i.relname, a.attnum;
    """)

    indexes = []
    for row in cursor.fetchall():
        indexes.append({
            'name': row[0],
            'column': row[1],
            'unique': row[2],
            'primary': row[3]
        })
    return indexes


def get_enums(cursor) -> List[Dict]:
    """Get all ENUM types."""
    cursor.execute("""
        SELECT
            t.typname AS enum_name,
            string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS enum_values
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public'
        GROUP BY t.typname
        ORDER BY t.typname;
    """)

    enums = []
    for row in cursor.fetchall():
        enums.append({
            'name': row[0],
            'values': row[1]
        })
    return enums


def get_table_row_count(cursor, table_name: str) -> int:
    """Get approximate row count for a table."""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        return cursor.fetchone()[0]
    except:
        return 0


def inspect_schema(database_url: str):
    """Inspect and display complete schema structure."""

    # Parse URL for display
    parsed = urlparse(database_url)
    safe_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}"

    print("=" * 80)
    print("POSTGRESQL SCHEMA INSPECTION")
    print("=" * 80)
    print(f"Database: {safe_url}\n")

    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Get database version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"PostgreSQL Version: {version.split(',')[0]}\n")

        # ==================== ENUMS ====================
        print("=" * 80)
        print("ENUM TYPES")
        print("=" * 80)
        enums = get_enums(cursor)
        if enums:
            for enum in enums:
                print(f"\n📊 {enum['name']}")
                print(f"   Values: {enum['values']}")
        else:
            print("No ENUM types found")
        print()

        # ==================== TABLES ====================
        tables = get_all_tables(cursor)
        print("=" * 80)
        print(f"TABLES ({len(tables)} total)")
        print("=" * 80)

        for table in tables:
            print(f"\n{'=' * 80}")
            print(f"📋 TABLE: {table}")
            print(f"{'=' * 80}")

            # Row count
            row_count = get_table_row_count(cursor, table)
            print(f"Rows: {row_count:,}")

            # Primary key
            pk = get_primary_key(cursor, table)
            if pk:
                print(f"Primary Key: {', '.join(pk)}")

            # Columns
            print("\n--- COLUMNS ---")
            columns = get_table_columns(cursor, table)
            for col in columns:
                nullable = "NULL" if col['nullable'] == 'YES' else "NOT NULL"
                type_str = col['udt_name'] if col['udt_name'] else col['type']
                if col['max_length']:
                    type_str += f"({col['max_length']})"

                default = f" DEFAULT {col['default']}" if col['default'] else ""
                print(f"  • {col['name']:30} {type_str:20} {nullable:10}{default}")

            # Foreign keys
            fks = get_foreign_keys(cursor, table)
            if fks:
                print("\n--- FOREIGN KEYS ---")
                for fk in fks:
                    print(f"  • {fk['column']} → {fk['references_table']}.{fk['references_column']} (ON DELETE {fk['on_delete']})")

            # Indexes
            indexes = get_indexes(cursor, table)
            if indexes:
                print("\n--- INDEXES ---")
                # Group by index name
                index_dict = {}
                for idx in indexes:
                    if idx['name'] not in index_dict:
                        index_dict[idx['name']] = {
                            'columns': [],
                            'unique': idx['unique'],
                            'primary': idx['primary']
                        }
                    index_dict[idx['name']]['columns'].append(idx['column'])

                for idx_name, idx_info in index_dict.items():
                    type_flags = []
                    if idx_info['primary']:
                        type_flags.append('PRIMARY KEY')
                    if idx_info['unique'] and not idx_info['primary']:
                        type_flags.append('UNIQUE')

                    flags = f" [{', '.join(type_flags)}]" if type_flags else ""
                    print(f"  • {idx_name}: ({', '.join(idx_info['columns'])}){flags}")

        # ==================== SUMMARY ====================
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total Tables: {len(tables)}")
        print(f"Total ENUMs: {len(enums)}")

        cursor.close()
        conn.close()

        print("\n✅ Schema inspection complete!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🔍 PostgreSQL Schema Inspector\n")

    # Get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        print("\nPlease set it from your Render dashboard:")
        print("  export DATABASE_URL='your-render-postgres-url'")
        print("\nOr run with:")
        print("  DATABASE_URL='your-url' python scripts/inspect_postgres_schema.py")
        sys.exit(1)

    if not inspect_schema(database_url):
        sys.exit(1)


if __name__ == "__main__":
    main()
