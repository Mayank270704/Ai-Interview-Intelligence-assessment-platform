"""Interview persistence foundation

Revision ID: 0001
Revises:
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_candidates_email", "candidates", ["email"])

    op.create_table(
        "resumes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("profile", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resumes_candidate_id", "resumes", ["candidate_id"])

    op.create_table(
        "resume_claims",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "resume_id",
            sa.String(length=36),
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("resume_evidence", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resume_claims_resume_id", "resume_claims", ["resume_id"])

    op.create_table(
        "interviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resume_id",
            sa.String(length=36),
            sa.ForeignKey("resumes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interviews_candidate_id", "interviews", ["candidate_id"])

    op.create_table(
        "interview_turns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "interview_id",
            sa.String(length=36),
            sa.ForeignKey("interviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("question", JSON_TYPE, nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("answer_analysis", JSON_TYPE, nullable=True),
        sa.Column("evaluation", JSON_TYPE, nullable=True),
        sa.Column("decision", JSON_TYPE, nullable=True),
        sa.Column("knowledge_state", JSON_TYPE, nullable=True),
        sa.Column("pending_claim_ids", JSON_TYPE, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("interview_id", "turn_number"),
    )
    op.create_index("ix_interview_turns_interview_id", "interview_turns", ["interview_id"])


def downgrade() -> None:
    op.drop_index("ix_interview_turns_interview_id", table_name="interview_turns")
    op.drop_table("interview_turns")
    op.drop_index("ix_interviews_candidate_id", table_name="interviews")
    op.drop_table("interviews")
    op.drop_index("ix_resume_claims_resume_id", table_name="resume_claims")
    op.drop_table("resume_claims")
    op.drop_index("ix_resumes_candidate_id", table_name="resumes")
    op.drop_table("resumes")
    op.drop_index("ix_candidates_email", table_name="candidates")
    op.drop_table("candidates")
