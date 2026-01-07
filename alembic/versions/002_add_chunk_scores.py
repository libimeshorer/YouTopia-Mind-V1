"""add_chunk_scores

Revision ID: 002
Revises: 001
Create Date: 2025-01-06

Adds chunk_scores table for reinforcement learning based on user feedback.
Chunks that receive positive feedback get boosted in future retrievals.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'chunk_scores',
        sa.Column('clone_id', UUID(as_uuid=True), sa.ForeignKey('clones.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_hash', sa.String(64), nullable=False),
        sa.Column('score', sa.Float, server_default='0.0', nullable=False),
        sa.Column('hit_count', sa.Integer, server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('clone_id', 'chunk_hash')
    )
    op.create_index('idx_chunk_scores_clone', 'chunk_scores', ['clone_id'])


def downgrade() -> None:
    op.drop_index('idx_chunk_scores_clone', table_name='chunk_scores')
    op.drop_table('chunk_scores')
