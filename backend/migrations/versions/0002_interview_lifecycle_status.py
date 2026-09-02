"""Interview lifecycle status

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interviews",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="created"),
    )
    op.alter_column("interviews", "status", server_default=None)


def downgrade() -> None:
    op.drop_column("interviews", "status")
