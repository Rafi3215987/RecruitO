"""add users.password_pending

Revision ID: a7c3e9f10b24
Revises: f1a2b3c4d5e6
Create Date: 2026-10-28

Marks accounts created on a candidate's behalf (hiring-manager CV import) that
still need the candidate to set a password via an emailed invite. The invite is
sent when the manager schedules their interview, not at import time.
"""
from alembic import op
import sqlalchemy as sa


revision = "a7c3e9f10b24"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_pending", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "password_pending")
