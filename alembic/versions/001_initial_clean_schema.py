"""initial_clean_schema

Revision ID: 001
Revises:
Create Date: 2025-12-19 00:00:00.000000

Clean schema without User model baggage.
Includes all improvements: ENUMs, first_name/last_name, email, file_hash, Sessions table.

WARNING: This migration DROPS ALL TABLES. It should only be run once during initial setup.
For safety, it requires ALLOW_DESTRUCTIVE_MIGRATIONS=true in production.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import os

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SAFETY CHECK: Prevent accidental data loss in production
    env = os.getenv('ENVIRONMENT', 'development')
    allow_destructive = os.getenv('ALLOW_DESTRUCTIVE_MIGRATIONS', 'false').lower() == 'true'

    if env == 'production' and not allow_destructive:
        raise Exception(
            "🛑 DESTRUCTIVE MIGRATION BLOCKED!\n\n"
            "This migration drops all existing tables and data.\n"
            "If you're absolutely sure you want to proceed, set:\n"
            "  ALLOW_DESTRUCTIVE_MIGRATIONS=true\n\n"
            "For production data, consider:\n"
            "  1. Backup your database first\n"
            "  2. Use a proper data migration strategy\n"
            "  3. Test in staging environment\n"
        )

    # Log warning for non-production environments
    if env != 'production':
        print(f"⚠️  Running destructive migration in {env} environment")
        print("⚠️  This will drop all existing tables!")

    # Drop all existing tables if they exist (fresh start)
    op.execute("DROP TABLE IF EXISTS data_sources CASCADE")
    op.execute("DROP TABLE IF EXISTS messages CASCADE")
    op.execute("DROP TABLE IF EXISTS training_status CASCADE")
    op.execute("DROP TABLE IF EXISTS integrations CASCADE")
    op.execute("DROP TABLE IF EXISTS insights CASCADE")
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS clones CASCADE")
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    
    # Drop old ENUMs if they exist
    op.execute("DROP TYPE IF EXISTS data_source_type CASCADE")
    op.execute("DROP TYPE IF EXISTS message_role CASCADE")
    op.execute("DROP TYPE IF EXISTS integration_status CASCADE")
    op.execute("DROP TYPE IF EXISTS integration_platform CASCADE")
    op.execute("DROP TYPE IF EXISTS insight_type CASCADE")
    op.execute("DROP TYPE IF EXISTS document_status CASCADE")
    op.execute("DROP TYPE IF EXISTS clone_status CASCADE")
    op.execute("DROP TYPE IF EXISTS session_status CASCADE")
    op.execute("DROP TYPE IF EXISTS session_platform CASCADE")
    
    # Create all ENUMs
    clone_status = postgresql.ENUM('active', 'inactive', name='clone_status', create_type=False)
    clone_status.create(op.get_bind(), checkfirst=True)
    
    document_status = postgresql.ENUM('pending', 'processing', 'complete', 'error', name='document_status', create_type=False)
    document_status.create(op.get_bind(), checkfirst=True)
    
    insight_type = postgresql.ENUM('text', 'voice', name='insight_type', create_type=False)
    insight_type.create(op.get_bind(), checkfirst=True)
    
    integration_platform = postgresql.ENUM('slack', 'gmail', 'email', 'notion', name='integration_platform', create_type=False)
    integration_platform.create(op.get_bind(), checkfirst=True)
    
    integration_status = postgresql.ENUM('connected', 'disconnected', 'error', name='integration_status', create_type=False)
    integration_status.create(op.get_bind(), checkfirst=True)
    
    message_role = postgresql.ENUM('external_user', 'clone', name='message_role', create_type=False)
    message_role.create(op.get_bind(), checkfirst=True)
    
    session_platform = postgresql.ENUM('slack', 'web', 'api', 'email', name='session_platform', create_type=False)
    session_platform.create(op.get_bind(), checkfirst=True)
    
    session_status = postgresql.ENUM('active', 'closed', name='session_status', create_type=False)
    session_status.create(op.get_bind(), checkfirst=True)
    
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('clerk_org_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tenants_clerk_org_id', 'tenants', ['clerk_org_id'])
    
    # Create clones table
    op.create_table(
        'clones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clerk_user_id', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', clone_status, nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clerk_user_id')
    )
    op.create_index('ix_clones_tenant_id', 'clones', ['tenant_id'])
    op.create_index('ix_clones_clerk_user_id', 'clones', ['clerk_user_id'], unique=True)
    op.create_index('ix_clones_email', 'clones', ['email'])
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_user_name', sa.String(), nullable=True),
        sa.Column('external_user_id', sa.String(), nullable=True),
        sa.Column('external_platform', session_platform, nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_message_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conversation_json', sa.JSON(), nullable=True),
        sa.Column('status', session_status, nullable=False, server_default='active'),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sessions_clone_id', 'sessions', ['clone_id'])
    op.create_index('ix_sessions_external_user_id', 'sessions', ['external_user_id'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.BigInteger(), nullable=False),
        sa.Column('role', message_role, nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('external_user_name', sa.String(), nullable=True),
        sa.Column('rag_context_json', sa.JSON(), nullable=True),
        sa.Column('feedback_rating', sa.Integer(), nullable=True),
        sa.Column('feedback_comment', sa.Text(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_clone_id', 'messages', ['clone_id'])
    op.create_index('ix_messages_session_id', 'messages', ['session_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('file_hash', sa.String(), nullable=True),
        sa.Column('status', document_status, nullable=False, server_default='pending'),
        sa.Column('s3_key', sa.String(), nullable=False),
        sa.Column('chunks_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_clone_id', 'documents', ['clone_id'])
    op.create_index('ix_documents_file_hash', 'documents', ['file_hash'])
    op.create_index('ix_documents_status', 'documents', ['status'])
    op.create_index('ix_documents_uploaded_at', 'documents', ['uploaded_at'])
    
    # Create insights table
    op.create_table(
        'insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('type', insight_type, nullable=False),
        sa.Column('audio_url', sa.String(), nullable=True),
        sa.Column('transcription_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_insights_clone_id', 'insights', ['clone_id'])
    op.create_index('ix_insights_created_at', 'insights', ['created_at'])
    
    # Create training_status table
    op.create_table(
        'training_status',
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_complete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('documents_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('insights_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('integrations_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('thresholds_json', sa.JSON(), nullable=False),
        sa.Column('achievements_json', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('clone_id')
    )

    # Set JSON defaults using raw SQL to avoid escaping issues
    # Use exec_driver_sql to bypass SQLAlchemy's bind parameter processing
    conn = op.get_bind()
    conn.exec_driver_sql("ALTER TABLE training_status ALTER COLUMN thresholds_json SET DEFAULT '{\"minDocuments\":1,\"minInsights\":1,\"minIntegrations\":1}'::json")
    conn.exec_driver_sql("ALTER TABLE training_status ALTER COLUMN achievements_json SET DEFAULT '[]'::json")
    
    # Create integrations table
    op.create_table(
        'integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', integration_platform, nullable=False),
        sa.Column('status', integration_status, nullable=False, server_default='disconnected'),
        sa.Column('credentials_encrypted', sa.Text(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('sync_settings_json', sa.JSON(), nullable=True, server_default=sa.text("'{}'::json")),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_integrations_clone_id', 'integrations', ['clone_id'])
    op.create_index('ix_integrations_platform', 'integrations', ['platform'])
    
    # Create data_sources table
    op.create_table(
        'data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_identifier', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('chunks_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('sync_settings_json', sa.JSON(), nullable=True, server_default=sa.text("'{}'::json")),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_sources_clone_id', 'data_sources', ['clone_id'])
    op.create_index('ix_data_sources_integration_id', 'data_sources', ['integration_id'])


def downgrade() -> None:
    # Drop all tables in reverse dependency order
    op.drop_table('data_sources')
    op.drop_table('integrations')
    op.drop_table('training_status')
    op.drop_table('insights')
    op.drop_table('documents')
    op.drop_table('messages')
    op.drop_table('sessions')
    op.drop_table('clones')
    op.drop_table('tenants')
    
    # Drop ENUMs
    op.execute('DROP TYPE IF EXISTS session_platform')
    op.execute('DROP TYPE IF EXISTS session_status')
    op.execute('DROP TYPE IF EXISTS message_role')
    op.execute('DROP TYPE IF EXISTS integration_status')
    op.execute('DROP TYPE IF EXISTS integration_platform')
    op.execute('DROP TYPE IF EXISTS insight_type')
    op.execute('DROP TYPE IF EXISTS document_status')
    op.execute('DROP TYPE IF EXISTS clone_status')
