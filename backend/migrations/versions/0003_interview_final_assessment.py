"""Interview final assessment

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "interview_assessments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "interview_id",
            sa.String(length=36),
            sa.ForeignKey("interviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("technical_knowledge", sa.Integer(), nullable=False),
        sa.Column("knowledge_depth", sa.Integer(), nullable=False),
        sa.Column("problem_solving", sa.Integer(), nullable=False),
        sa.Column("communication", sa.Integer(), nullable=False),
        sa.Column("resume_claim_accuracy", sa.Integer(), nullable=True),
        sa.Column("strengths", JSON_TYPE, nullable=False),
        sa.Column("weaknesses", JSON_TYPE, nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("turns_assessed", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("interview_id", name="uq_interview_assessments_interview_id"),
    )
    op.create_index(
        "ix_interview_assessments_interview_id", "interview_assessments", ["interview_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_interview_assessments_interview_id", table_name="interview_assessments")
    op.drop_table("interview_assessments")
