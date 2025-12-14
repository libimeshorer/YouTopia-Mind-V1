"""add_processed_at_to_documents

Revision ID: 4928b3696f8b
Revises: 46afbdc12b31
Create Date: 2025-12-14 16:03:45.558998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4928b3696f8b'
down_revision: Union[str, None] = '46afbdc12b31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add processed_at column to documents table
    op.add_column(
        'documents',
        sa.Column('processed_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    # Remove processed_at column from documents table
    op.drop_column('documents', 'processed_at')
