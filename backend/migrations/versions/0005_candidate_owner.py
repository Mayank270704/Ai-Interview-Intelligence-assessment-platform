"""Candidate ownership

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_candidates_owner_user_id", "candidates", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_candidates_owner_user_id", table_name="candidates")
    op.drop_column("candidates", "owner_user_id")
