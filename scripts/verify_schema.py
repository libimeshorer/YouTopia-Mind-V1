"""Verify database schema matches models exactly"""

from sqlalchemy import inspect
from src.database.db import engine
from src.utils.logging import get_logger
import sys

logger = get_logger(__name__)


def verify_schema():
    """Verify database schema matches model definitions"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # Required tables
    required_tables = {
        'tenants': ['id', 'name', 'clerk_org_id', 'created_at', 'updated_at'],
        'clones': ['id', 'tenant_id', 'clerk_user_id', 'first_name', 'last_name', 'email', 'description', 'status', 'created_at', 'updated_at'],
        'sessions': ['id', 'clone_id', 'external_user_name', 'external_user_id', 'external_platform', 'started_at', 'last_message_at', 'message_count', 'conversation_json', 'status'],
        'messages': ['id', 'clone_id', 'session_id', 'role', 'content', 'external_user_name', 'rag_context_json', 'feedback_rating', 'feedback_comment', 'tokens_used', 'response_time_ms', 'created_at'],
        'documents': ['id', 'clone_id', 'name', 'size', 'type', 'file_hash', 'status', 's3_key', 'chunks_count', 'uploaded_at', 'processed_at', 'error_message'],
        'insights': ['id', 'clone_id', 'content', 'type', 'audio_url', 'transcription_id', 'created_at', 'updated_at'],
        'training_status': ['clone_id', 'is_complete', 'progress', 'documents_count', 'insights_count', 'integrations_count', 'thresholds_json', 'achievements_json', 'updated_at'],
        'integrations': ['id', 'clone_id', 'platform', 'status', 'credentials_encrypted', 'last_sync_at', 'sync_settings_json', 'created_at', 'updated_at'],
        'data_sources': ['id', 'clone_id', 'integration_id', 'source_type', 'source_identifier', 'display_name', 'is_active', 'chunks_count', 'last_synced_at', 'last_error', 'sync_settings_json', 'created_at', 'updated_at'],
    }
    
    errors = []
    warnings = []
    
    # Check all tables exist
    for table_name, required_columns in required_tables.items():
        if table_name not in existing_tables:
            errors.append(f"❌ Table '{table_name}' is missing")
            continue
        
        print(f"✓ Table '{table_name}' exists")
        
        # Check columns
        actual_columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        for col in required_columns:
            if col not in actual_columns:
                errors.append(f"❌ Table '{table_name}' missing column '{col}'")
            else:
                print(f"  ✓ Column '{col}' exists")
        
        # Check for unexpected columns (like user_id that should be removed)
        deprecated_columns = ['user_id']
        for col in actual_columns:
            if col in deprecated_columns:
                warnings.append(f"⚠️  Table '{table_name}' has deprecated column '{col}' (should be removed)")
    
    # Check for deprecated 'users' table
    if 'users' in existing_tables:
        warnings.append("⚠️  Deprecated 'users' table still exists (should be removed)")
    
    # Check primary keys
    pk_checks = {
        'tenants': ['id'],
        'clones': ['id'],
        'sessions': ['id'],
        'documents': ['id'],
        'insights': ['id'],
        'integrations': ['id'],
        'training_status': ['clone_id'],  # Special case - clone_id is PK
        'messages': ['id'],
        'data_sources': ['id'],
    }
    
    for table_name, expected_pk in pk_checks.items():
        if table_name in existing_tables:
            pk = inspector.get_pk_constraint(table_name)
            if pk['constrained_columns'] != expected_pk:
                errors.append(f"❌ Table '{table_name}' has wrong primary key: {pk['constrained_columns']} (expected {expected_pk})")
            else:
                print(f"✓ Table '{table_name}' has correct primary key: {expected_pk}")
    
    # Check ENUMs exist
    required_enums = [
        'clone_status',
        'document_status',
        'insight_type',
        'integration_platform',
        'integration_status',
        'message_role',
        'session_platform',
        'session_status',
    ]
    
    with engine.connect() as conn:
        for enum_name in required_enums:
            result = conn.execute(
                f"SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}')"
            ).scalar()
            if result:
                print(f"✓ ENUM '{enum_name}' exists")
            else:
                errors.append(f"❌ ENUM '{enum_name}' is missing")
    
    print("\n" + "="*50)
    if errors:
        print("SCHEMA VALIDATION FAILED:")
        for error in errors:
            print(error)
        if warnings:
            print("\nWARNINGS:")
            for warning in warnings:
                print(warning)
        return False
    else:
        print("✓✓✓ ALL SCHEMA CHECKS PASSED ✓✓✓")
        if warnings:
            print("\nWARNINGS (non-critical):")
            for warning in warnings:
                print(warning)
        return True


if __name__ == "__main__":
    if not verify_schema():
        sys.exit(1)
