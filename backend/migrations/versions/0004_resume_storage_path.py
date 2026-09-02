"""Resume storage path

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column("storage_path", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resumes", "storage_path")
