"""Row-level security hardening

Enables RLS on all application tables and adds owner-scoped policies for the
`authenticated` Postgres role, keyed off `auth.uid()`. This is defense in
depth: the backend's own database connection uses a role that owns these
tables (and carries BYPASSRLS), so these policies do not affect the
application's existing read/write path -- they only constrain any future or
incidental access through Supabase's `anon`/`authenticated` Postgres roles
(e.g. PostgREST), which the application does not currently use for this data.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-02
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


# Each entry: (table, ownership predicate referencing the table's own columns)
_POLICIES = {
    "candidates": "owner_user_id = auth.uid()::text",
    "resumes": (
        "EXISTS (SELECT 1 FROM candidates c WHERE c.id = resumes.candidate_id "
        "AND c.owner_user_id = auth.uid()::text)"
    ),
    "resume_claims": (
        "EXISTS (SELECT 1 FROM resumes r JOIN candidates c ON c.id = r.candidate_id "
        "WHERE r.id = resume_claims.resume_id AND c.owner_user_id = auth.uid()::text)"
    ),
    "interviews": (
        "EXISTS (SELECT 1 FROM candidates c WHERE c.id = interviews.candidate_id "
        "AND c.owner_user_id = auth.uid()::text)"
    ),
    "interview_turns": (
        "EXISTS (SELECT 1 FROM interviews i JOIN candidates c ON c.id = i.candidate_id "
        "WHERE i.id = interview_turns.interview_id AND c.owner_user_id = auth.uid()::text)"
    ),
    "interview_assessments": (
        "EXISTS (SELECT 1 FROM interviews i JOIN candidates c ON c.id = i.candidate_id "
        "WHERE i.id = interview_assessments.interview_id AND c.owner_user_id = auth.uid()::text)"
    ),
}


def upgrade() -> None:
    for table, predicate in _POLICIES.items():
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_owner_access ON {table} "
            f"FOR ALL TO authenticated USING ({predicate}) WITH CHECK ({predicate})"
        )


def downgrade() -> None:
    for table in _POLICIES:
        op.execute(f"DROP POLICY IF EXISTS {table}_owner_access ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
