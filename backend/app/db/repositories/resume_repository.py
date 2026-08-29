"""Resume repository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Resume, ResumeClaim
from app.schemas.resume import CandidateProfile


def create_resume(
    session: Session,
    candidate_id: str,
    profile: CandidateProfile,
) -> Resume:
    """Store a candidate profile and give every resume claim a stable identifier."""
    resume = Resume(candidate_id=candidate_id, profile={})
    session.add(resume)
    session.flush()

    identified_claims = []
    for claim in profile.claims:
        row = ResumeClaim(
            resume_id=resume.id,
            claim_text=claim.claim_text,
            category=claim.category,
            context=claim.context,
            resume_evidence=claim.resume_evidence,
        )
        session.add(row)
        session.flush()
        identified_claims.append(claim.model_copy(update={"claim_id": row.id}))

    resume.profile = profile.model_copy(
        update={"claims": identified_claims}
    ).model_dump(mode="json")
    session.flush()
    return resume


def get_resume(session: Session, resume_id: str) -> Resume | None:
    """Load a resume by id."""
    return session.get(Resume, resume_id)


def load_candidate_profile(session: Session, resume_id: str) -> CandidateProfile | None:
    """Load the stored candidate profile, including the stable claim identifiers."""
    resume = session.get(Resume, resume_id)
    if resume is None:
        return None
    return CandidateProfile.model_validate(resume.profile)
