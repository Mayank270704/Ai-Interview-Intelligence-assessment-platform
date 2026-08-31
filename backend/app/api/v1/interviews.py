"""Interview API routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_session
from app.db.repositories import (
    candidate_repository,
    interview_repository,
    resume_repository,
)
from app.schemas.interview import (
    InterviewAnswerRequest,
    InterviewQuestionResponse,
    InterviewStartRequest,
    InterviewStateResponse,
)
from app.services.interview.turn_service import InterviewTurnService

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewQuestionResponse)
def start_interview(
    request: InterviewStartRequest,
    session: Session = Depends(get_session),
) -> InterviewQuestionResponse:
    candidate_id = request.candidate_id
    resume_id = request.resume_id
    profile = request.candidate_profile

    if resume_id:
        resume = resume_repository.get_resume(session, resume_id)
        if resume is None:
            raise HTTPException(status_code=404, detail="Resume not found")
        candidate_id = resume.candidate_id
        profile = resume_repository.load_candidate_profile(session, resume_id)
    elif profile:
        if candidate_id is None:
            candidate = candidate_repository.create_candidate(
                session,
                full_name=profile.identity.full_name,
                email=profile.identity.email,
            )
            candidate_id = candidate.id
        elif candidate_repository.get_candidate(session, candidate_id) is None:
            raise HTTPException(status_code=404, detail="Candidate not found")

        resume = resume_repository.create_resume(session, candidate_id, profile)
        resume_id = resume.id
        profile = resume_repository.load_candidate_profile(session, resume_id)
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either resume_id or candidate_profile to start an interview",
        )

    interview = interview_repository.create_interview(
        session,
        candidate_id=candidate_id,
        resume_id=resume_id,
        objective=request.objective,
        difficulty=request.difficulty,
    )
    service = InterviewTurnService(
        interview_id=interview.id,
        interview_objective=interview.objective,
        candidate_profile=profile,
        difficulty=interview.difficulty,
        session=session,
    )
    question = service.start_interview()

    return InterviewQuestionResponse(
        interview_id=interview.id,
        candidate_id=candidate_id,
        resume_id=resume_id,
        difficulty=service.difficulty,
        question=question,
    )


@router.post("/{interview_id}/answers", response_model=InterviewQuestionResponse)
def submit_answer(
    interview_id: str,
    request: InterviewAnswerRequest,
    session: Session = Depends(get_session),
) -> InterviewQuestionResponse:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    service = InterviewTurnService.load(session, interview_id)
    question = service.submit_answer(request.answer)

    return InterviewQuestionResponse(
        interview_id=interview.id,
        candidate_id=interview.candidate_id,
        resume_id=interview.resume_id,
        difficulty=service.difficulty,
        question=question,
    )


@router.get("/{interview_id}", response_model=InterviewStateResponse)
def get_interview(
    interview_id: str,
    session: Session = Depends(get_session),
) -> InterviewStateResponse:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    service = InterviewTurnService.load(session, interview_id)
    turns = interview_repository.get_turns(session, interview_id)
    return InterviewStateResponse(
        interview_id=interview.id,
        candidate_id=interview.candidate_id,
        resume_id=interview.resume_id,
        objective=interview.objective,
        difficulty=service.difficulty,
        current_question=service.current_question,
        knowledge_state=service.knowledge_state.model_dump(mode="json"),
        turns=[_turn_to_dict(turn) for turn in turns],
    )


def _turn_to_dict(turn: Any) -> dict[str, Any]:
    return {
        "id": turn.id,
        "turn_number": turn.turn_number,
        "question": turn.question,
        "answer": turn.answer,
        "answer_analysis": turn.answer_analysis,
        "evaluation": turn.evaluation,
        "decision": turn.decision,
        "knowledge_state": turn.knowledge_state,
        "pending_claim_ids": turn.pending_claim_ids,
        "created_at": turn.created_at.isoformat(),
    }
