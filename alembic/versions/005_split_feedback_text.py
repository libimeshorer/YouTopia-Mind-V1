"""split_feedback_text

Revision ID: 005
Revises: 004
Create Date: 2025-01-17

Split feedback_text into separate fields for content and style feedback:
- Rename feedback_text -> content_feedback_text
- Add style_feedback_text for style-specific notes
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename feedback_text to content_feedback_text
    op.alter_column('messages', 'feedback_text', new_column_name='content_feedback_text')

    # Add style_feedback_text for style-specific notes
    op.add_column('messages', sa.Column('style_feedback_text', sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'style_feedback_text')
    op.alter_column('messages', 'content_feedback_text', new_column_name='feedback_text')
