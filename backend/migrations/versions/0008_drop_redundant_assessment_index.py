"""Drop the redundant interview_assessments index

Migration 0003 created both a UNIQUE constraint and a plain index on
interview_assessments.interview_id. In PostgreSQL a unique constraint is already
backed by its own unique index, so the plain index served no query the
constraint's index could not, and only cost write amplification and storage.

Uniqueness is unaffected: it was and remains enforced by
uq_interview_assessments_interview_id.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-03
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF EXISTS: databases created from the models rather than from migration
    # 0003 never had this index.
    op.execute("DROP INDEX IF EXISTS ix_interview_assessments_interview_id")


def downgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_interview_assessments_interview_id "
        "ON interview_assessments (interview_id)"
    )
