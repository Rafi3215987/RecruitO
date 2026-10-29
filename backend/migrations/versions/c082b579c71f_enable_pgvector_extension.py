"""enable pgvector extension

Revision ID: c082b579c71f
Revises: bcd162c836f9
Create Date: 2026-10-07 12:55:55.387650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c082b579c71f'
down_revision: Union[str, Sequence[str], None] = 'bcd162c836f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Downgrade schema."""
    pass
