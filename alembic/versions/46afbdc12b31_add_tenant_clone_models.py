"""add tenant clone models

Revision ID: 46afbdc12b31
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '46afbdc12b31'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Helper function to check if table exists
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Create users table if it doesn't exist (DEPRECATED but needed for migration)
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('clerk_user_id', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_clerk_user_id'), 'users', ['clerk_user_id'], unique=True)
    
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('clerk_org_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenants_clerk_org_id'), 'tenants', ['clerk_org_id'], unique=False)
    
    # Create clones table
    op.create_table(
        'clones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clerk_user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clerk_user_id')
    )
    op.create_index(op.f('ix_clones_tenant_id'), 'clones', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_clones_clerk_user_id'), 'clones', ['clerk_user_id'], unique=True)
    
    # Create documents table if it doesn't exist
    if 'documents' not in existing_tables:
        op.create_table(
            'documents',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('size', sa.Integer(), nullable=False),
            sa.Column('type', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('s3_key', sa.String(), nullable=False),
            sa.Column('chunks_count', sa.Integer(), default=0),
            sa.Column('uploaded_at', sa.DateTime(), nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
    
    # Add clone_id column to documents (nullable initially for migration)
    # Check if column exists before adding
    documents_columns = [col['name'] for col in inspector.get_columns('documents')] if 'documents' in existing_tables else []
    if 'clone_id' not in documents_columns:
        op.add_column('documents', sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=True))
        op.create_index(op.f('ix_documents_clone_id'), 'documents', ['clone_id'], unique=False)
        op.create_foreign_key('fk_documents_clone_id', 'documents', 'clones', ['clone_id'], ['id'])
    
    # Create insights table if it doesn't exist
    if 'insights' not in existing_tables:
        op.create_table(
            'insights',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('type', sa.String(), nullable=False),
            sa.Column('audio_url', sa.String(), nullable=True),
            sa.Column('transcription_id', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_insights_user_id'), 'insights', ['user_id'], unique=False)
    
    # Add clone_id column to insights (nullable initially for migration)
    insights_columns = [col['name'] for col in inspector.get_columns('insights')] if 'insights' in existing_tables else []
    if 'clone_id' not in insights_columns:
        op.add_column('insights', sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=True))
        op.create_index(op.f('ix_insights_clone_id'), 'insights', ['clone_id'], unique=False)
        op.create_foreign_key('fk_insights_clone_id', 'insights', 'clones', ['clone_id'], ['id'])
    
    # Create integrations table if it doesn't exist
    if 'integrations' not in existing_tables:
        op.create_table(
            'integrations',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('type', sa.String(), nullable=False),
            sa.Column('platform', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('credentials_json', sa.JSON(), nullable=True),
            sa.Column('last_sync_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_integrations_user_id'), 'integrations', ['user_id'], unique=False)
    
    # Add clone_id column to integrations (nullable initially for migration)
    integrations_columns = [col['name'] for col in inspector.get_columns('integrations')] if 'integrations' in existing_tables else []
    if 'clone_id' not in integrations_columns:
        op.add_column('integrations', sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=True))
        op.create_index(op.f('ix_integrations_clone_id'), 'integrations', ['clone_id'], unique=False)
        op.create_foreign_key('fk_integrations_clone_id', 'integrations', 'clones', ['clone_id'], ['id'])
    
    # Create training_status table if it doesn't exist
    if 'training_status' not in existing_tables:
        op.create_table(
            'training_status',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('is_complete', sa.Boolean(), nullable=False),
            sa.Column('progress', sa.Float(), nullable=False),
            sa.Column('documents_count', sa.Integer(), nullable=False),
            sa.Column('insights_count', sa.Integer(), nullable=False),
            sa.Column('integrations_count', sa.Integer(), nullable=False),
            sa.Column('thresholds_json', sa.JSON(), nullable=True),
            sa.Column('achievements_json', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_training_status_user_id'), 'training_status', ['user_id'], unique=True)
    
    # Add clone_id column to training_status (nullable initially for migration)
    training_status_columns = [col['name'] for col in inspector.get_columns('training_status')] if 'training_status' in existing_tables else []
    if 'clone_id' not in training_status_columns:
        op.add_column('training_status', sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=True))
        # Note: We can't change the primary key directly, so we'll need to handle this in the migration script
        # For now, we'll keep both user_id and clone_id, and the migration script will handle the transition


def downgrade() -> None:
    # Remove clone_id columns
    op.drop_constraint('fk_integrations_clone_id', 'integrations', type_='foreignkey')
    op.drop_index(op.f('ix_integrations_clone_id'), table_name='integrations')
    op.drop_column('integrations', 'clone_id')
    
    op.drop_constraint('fk_insights_clone_id', 'insights', type_='foreignkey')
    op.drop_index(op.f('ix_insights_clone_id'), table_name='insights')
    op.drop_column('insights', 'clone_id')
    
    op.drop_constraint('fk_documents_clone_id', 'documents', type_='foreignkey')
    op.drop_index(op.f('ix_documents_clone_id'), table_name='documents')
    op.drop_column('documents', 'clone_id')
    
    op.drop_column('training_status', 'clone_id')
    
    # Drop clones table
    op.drop_index(op.f('ix_clones_clerk_user_id'), table_name='clones')
    op.drop_index(op.f('ix_clones_tenant_id'), table_name='clones')
    op.drop_table('clones')
    
    # Drop tenants table
    op.drop_index(op.f('ix_tenants_clerk_org_id'), table_name='tenants')
    op.drop_table('tenants')
