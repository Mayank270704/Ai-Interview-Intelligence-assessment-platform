"""Candidate consent for ML training data use

Adds an explicit, opt-in consent flag. It defaults to false, so every existing
row and every candidate created without an explicit choice is ineligible for
training-data export -- consent is never inferred from silence.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column(
            "ml_training_consent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("candidates", "ml_training_consent")
