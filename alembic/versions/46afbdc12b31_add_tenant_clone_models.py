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
    
    # Add clone_id columns to existing tables (nullable initially for migration)
    op.add_column('documents', sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_documents_clone_id'), 'documents', ['clone_id'], unique=False)
    op.create_foreign_key('fk_documents_clone_id', 'documents', 'clones', ['clone_id'], ['id'])
    
    op.add_column('insights', sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_insights_clone_id'), 'insights', ['clone_id'], unique=False)
    op.create_foreign_key('fk_insights_clone_id', 'insights', 'clones', ['clone_id'], ['id'])
    
    op.add_column('integrations', sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_integrations_clone_id'), 'integrations', ['clone_id'], unique=False)
    op.create_foreign_key('fk_integrations_clone_id', 'integrations', 'clones', ['clone_id'], ['id'])
    
    # Update training_status table - change primary key from user_id to clone_id
    # First, add clone_id column
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
