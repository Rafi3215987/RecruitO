"""add candidate profile details

Revision ID: 9a4c2f7d1b6e
Revises: 375b36b827dd
Create Date: 2026-10-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a4c2f7d1b6e"
down_revision: Union[str, Sequence[str], None] = "375b36b827dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_profiles",
        sa.Column("contact_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("phone_number", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("certificate_full_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "education_qualification",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("institution_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("department", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("graduation_year", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_profiles", "graduation_year")
    op.drop_column("candidate_profiles", "department")
    op.drop_column("candidate_profiles", "institution_name")
    op.drop_column("candidate_profiles", "education_qualification")
    op.drop_column("candidate_profiles", "certificate_full_name")
    op.drop_column("candidate_profiles", "phone_number")
    op.drop_column("candidate_profiles", "contact_email")
