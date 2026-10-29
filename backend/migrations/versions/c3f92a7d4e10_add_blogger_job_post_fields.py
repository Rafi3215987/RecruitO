"""add Blogger job post tracking

Revision ID: c3f92a7d4e10
Revises: 541c39831cda
Create Date: 2026-10-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3f92a7d4e10"
down_revision: Union[str, Sequence[str], None] = "541c39831cda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("external_post_provider", sa.String(length=40), nullable=True))
    op.add_column("jobs", sa.Column("blogger_post_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "blogger_post_id")
    op.drop_column("jobs", "external_post_provider")
