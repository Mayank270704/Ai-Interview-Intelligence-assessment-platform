"""Database models registered on the shared declarative metadata."""

from app.db.models.assessment import InterviewAssessment
from app.db.models.candidate import Candidate
from app.db.models.claim import ResumeClaim
from app.db.models.interview import Interview, InterviewTurn
from app.db.models.resume import Resume

__all__ = [
    "Candidate",
    "Interview",
    "InterviewAssessment",
    "InterviewTurn",
    "Resume",
    "ResumeClaim",
]
