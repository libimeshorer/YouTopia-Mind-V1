"""add_enhanced_feedback

Revision ID: 003
Revises: 002
Create Date: 2025-01-06

Adds enhanced feedback columns to messages table:
- style_rating: Separate rating for "sounds like me" (owner only)
- feedback_source: Track who gave feedback (owner vs external_user)
- feedback_text: Optional text correction on negative feedback
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add style rating (-1, 0, 1, or NULL)
    op.add_column('messages', sa.Column('style_rating', sa.Integer, nullable=True))

    # Add feedback source ('owner' or 'external_user')
    op.add_column('messages', sa.Column('feedback_source', sa.String(20), nullable=True))

    # Add feedback text (optional correction text on negative feedback)
    op.add_column('messages', sa.Column('feedback_text', sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'feedback_text')
    op.drop_column('messages', 'feedback_source')
    op.drop_column('messages', 'style_rating')
