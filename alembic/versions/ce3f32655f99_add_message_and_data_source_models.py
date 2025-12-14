"""add_message_and_data_source_models

Revision ID: ce3f32655f99
Revises: 4928b3696f8b
Create Date: 2025-12-14 16:31:27.546907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce3f32655f99'
down_revision: Union[str, None] = '4928b3696f8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('clone_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('rag_context_json', sa.JSON(), nullable=True),
        sa.Column('feedback_rating', sa.Integer(), nullable=True),
        sa.Column('feedback_comment', sa.Text(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    )
    op.create_index(op.f('ix_messages_clone_id'), 'messages', ['clone_id'], unique=False)
    op.create_index(op.f('ix_messages_user_id'), 'messages', ['user_id'], unique=False)
    op.create_index(op.f('ix_messages_session_id'), 'messages', ['session_id'], unique=False)
    op.create_index(op.f('ix_messages_created_at'), 'messages', ['created_at'], unique=False)
    
    # Create data_sources table
    op.create_table(
        'data_sources',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('clone_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('integration_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_identifier', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('chunks_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('sync_settings_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ),
        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    )
    op.create_index(op.f('ix_data_sources_clone_id'), 'data_sources', ['clone_id'], unique=False)
    op.create_index(op.f('ix_data_sources_integration_id'), 'data_sources', ['integration_id'], unique=False)
    op.create_index(op.f('ix_data_sources_user_id'), 'data_sources', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop data_sources table
    op.drop_index(op.f('ix_data_sources_user_id'), table_name='data_sources')
    op.drop_index(op.f('ix_data_sources_integration_id'), table_name='data_sources')
    op.drop_index(op.f('ix_data_sources_clone_id'), table_name='data_sources')
    op.drop_table('data_sources')
    
    # Drop messages table
    op.drop_index(op.f('ix_messages_created_at'), table_name='messages')
    op.drop_index(op.f('ix_messages_session_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_user_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_clone_id'), table_name='messages')
    op.drop_table('messages')
