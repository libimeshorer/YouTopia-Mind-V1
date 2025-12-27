"""add_is_core_to_documents

Revision ID: 002
Revises: 001
Create Date: 2025-12-27 00:00:00.000000

Adds is_core boolean column to documents table to mark foundational/core documents.
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_core column to documents table."""
    op.add_column(
        'documents',
        sa.Column('is_core', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    """Remove is_core column from documents table."""
    op.drop_column('documents', 'is_core')
