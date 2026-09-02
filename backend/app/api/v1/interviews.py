"""Interview API routes."""

import base64
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.voice.client import VoiceClient
from app.core.constants import (
    INTERVIEW_STATUS_COMPLETED,
    INTERVIEW_STATUS_IN_PROGRESS,
)
from app.core.exceptions import InterviewPipelineError
from app.core.security import ensure_owner, get_current_user
from app.db.database import get_session
from app.db.models import Interview
from app.db.repositories import (
    assessment_repository,
    candidate_repository,
    interview_repository,
    resume_repository,
)
from app.db.supabase_auth import AuthenticatedUser
from app.schemas.assessment import FinalAssessment
from app.schemas.interview import (
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewQuestionResponse,
    InterviewStartRequest,
    InterviewStateResponse,
    InterviewTurnResponse,
    AnsweredTurnResponse,
)
from app.schemas.question import GeneratedQuestion
from app.schemas.video import VideoAnswerResponse
from app.schemas.voice import QuestionAudioResponse, VoiceAnswerResponse
from app.services.interview import assessment_service
from app.services.interview.turn_service import InterviewTurnService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interviews", tags=["interviews"])

MAX_VOICE_ANSWER_BYTES = 15 * 1024 * 1024
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/webm",
    "audio/ogg",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
}

MAX_VIDEO_ANSWER_BYTES = 50 * 1024 * 1024
ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
}


def _base_mime_type(content_type: str | None) -> str:
    """Normalize an upload's content type for allowlist checks.

    Browser MediaRecorder uploads carry codec parameters (e.g.
    'audio/webm;codecs=opus'), which name the same media type as the bare form.
    """
    return (content_type or "").split(";")[0].strip().lower()


def _execute_answer_turn(
    session: Session,
    interview: Interview,
    request_turn_id: str,
    answer: str,
) -> tuple[InterviewTurnService, GeneratedQuestion]:
    """Validate turn state and run one answer submission through the shared pipeline.

    Used by both the text and voice answer routes so the two transports stay
    behaviorally identical -- only how the answer text is obtained differs.
    """
    if interview.status == INTERVIEW_STATUS_COMPLETED:
        raise HTTPException(
            status_code=409, detail="Interview has already been completed and cannot accept new answers"
        )
    if interview.status != INTERVIEW_STATUS_IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Interview is not in progress")

    service = InterviewTurnService.load(session, interview.id)
    current_turn_id = service.current_turn_id
    if current_turn_id is None:
        raise HTTPException(status_code=409, detail="Interview has no pending turn")
    if request_turn_id != current_turn_id:
        requested_turn = interview_repository.get_turn(session, request_turn_id)
        if requested_turn is None:
            raise HTTPException(status_code=404, detail="Interview turn not found")
        if requested_turn.interview_id != interview.id:
            raise HTTPException(
                status_code=400,
                detail="Interview turn does not belong to this interview",
            )
        if requested_turn.answer is not None:
            raise HTTPException(status_code=409, detail="Interview turn already answered")
        raise HTTPException(status_code=409, detail="Interview turn is not current")

    try:
        question = service.submit_answer(answer)
    except InterviewPipelineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if (
        service.last_answered_turn is None
        or service.last_answer_analysis is None
        or service.last_evaluation is None
        or service.last_decision is None
        or service.current_turn_id is None
    ):
        raise HTTPException(status_code=500, detail="Interview turn was not persisted")

    return service, question


@router.post("", response_model=InterviewQuestionResponse)
def start_interview(
    request: InterviewStartRequest,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewQuestionResponse:
    candidate_id = request.candidate_id
    resume_id = request.resume_id
    profile = request.candidate_profile

    if resume_id:
        resume = resume_repository.get_resume(session, resume_id)
        if resume is None:
            raise HTTPException(status_code=404, detail="Resume not found")
        if candidate_id is not None and candidate_id != resume.candidate_id:
            raise HTTPException(
                status_code=400,
                detail="Resume does not belong to the supplied candidate",
            )
        ensure_owner(resume.candidate.owner_user_id, current_user)
        candidate_id = resume.candidate_id
        profile = resume_repository.load_candidate_profile(session, resume_id)
    elif profile:
        if candidate_id is None:
            candidate = candidate_repository.create_candidate(
                session,
                full_name=profile.identity.full_name,
                email=profile.identity.email,
                owner_user_id=current_user.id,
            )
            candidate_id = candidate.id
        else:
            existing_candidate = candidate_repository.get_candidate(session, candidate_id)
            if existing_candidate is None:
                raise HTTPException(status_code=404, detail="Candidate not found")
            ensure_owner(existing_candidate.owner_user_id, current_user)

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
    try:
        question = service.start_interview()
    except InterviewPipelineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    turn_id = service.current_turn_id
    if turn_id is None:
        raise HTTPException(status_code=500, detail="Interview turn was not persisted")

    interview_repository.mark_in_progress(session, interview.id)

    return InterviewQuestionResponse(
        interview_id=interview.id,
        candidate_id=candidate_id,
        resume_id=resume_id,
        difficulty=service.difficulty,
        status=INTERVIEW_STATUS_IN_PROGRESS,
        turn_id=turn_id,
        question=question,
    )


@router.post("/{interview_id}/answers", response_model=InterviewAnswerResponse)
def submit_answer(
    interview_id: str,
    request: InterviewAnswerRequest,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewAnswerResponse:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    ensure_owner(interview.candidate.owner_user_id, current_user)

    service, question = _execute_answer_turn(session, interview, request.turn_id, request.answer)

    return InterviewAnswerResponse(
        interview_id=interview.id,
        answered_turn=AnsweredTurnResponse(
            turn_id=service.last_answered_turn.id,
            turn_number=service.last_answered_turn.turn_number,
            question=service.last_answered_turn.question,
            answer=service.last_answered_turn.answer,
        ),
        answer_analysis=service.last_answer_analysis,
        evaluation=service.last_evaluation,
        interviewer_decision=service.last_decision,
        next_turn_id=service.current_turn_id,
        next_question=question,
        difficulty=service.difficulty,
        status=interview.status,
        knowledge_state=service.knowledge_state,
    )


@router.get("/{interview_id}/question-audio", response_model=QuestionAudioResponse)
def get_question_audio(
    interview_id: str,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> QuestionAudioResponse:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    ensure_owner(interview.candidate.owner_user_id, current_user)

    service = InterviewTurnService.load(session, interview_id)
    if service.current_question is None or service.current_turn_id is None:
        raise HTTPException(status_code=409, detail="Interview has no pending question")

    try:
        audio_bytes, mime_type = VoiceClient().synthesize(service.current_question.question)
    except (ValueError, RuntimeError) as exc:
        logger.warning("Speech synthesis failed for interview %s: %s", interview_id, exc)
        raise HTTPException(
            status_code=502, detail="Failed to generate audio for this question"
        ) from exc

    return QuestionAudioResponse(
        turn_id=service.current_turn_id,
        audio_base64=base64.b64encode(audio_bytes).decode("ascii"),
        audio_mime_type=mime_type,
    )


@router.post("/{interview_id}/voice-answers", response_model=VoiceAnswerResponse)
def submit_voice_answer(
    interview_id: str,
    turn_id: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> VoiceAnswerResponse:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    ensure_owner(interview.candidate.owner_user_id, current_user)

    audio_bytes = file.file.read(MAX_VOICE_ANSWER_BYTES + 1)
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Uploaded audio is empty")
    if len(audio_bytes) > MAX_VOICE_ANSWER_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded audio is too large")
    mime_type = _base_mime_type(file.content_type)
    if mime_type not in ALLOWED_AUDIO_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Uploaded file must be a supported audio format")

    voice_client = VoiceClient()
    try:
        transcribed_answer = voice_client.transcribe(audio_bytes, mime_type)
    except (ValueError, RuntimeError) as exc:
        logger.warning("Transcription failed for interview %s: %s", interview_id, exc)
        raise HTTPException(
            status_code=502, detail="Failed to transcribe the recorded answer"
        ) from exc

    service, question = _execute_answer_turn(session, interview, turn_id, transcribed_answer)

    try:
        next_audio_bytes, next_audio_mime = voice_client.synthesize(question.question)
    except (ValueError, RuntimeError) as exc:
        logger.warning("Speech synthesis failed for interview %s: %s", interview_id, exc)
        raise HTTPException(
            status_code=502, detail="Failed to generate audio for the next question"
        ) from exc

    return VoiceAnswerResponse(
        interview_id=interview.id,
        answered_turn=AnsweredTurnResponse(
            turn_id=service.last_answered_turn.id,
            turn_number=service.last_answered_turn.turn_number,
            question=service.last_answered_turn.question,
            answer=service.last_answered_turn.answer,
        ),
        answer_analysis=service.last_answer_analysis,
        evaluation=service.last_evaluation,
        interviewer_decision=service.last_decision,
        next_turn_id=service.current_turn_id,
        next_question=question,
        difficulty=service.difficulty,
        status=interview.status,
        knowledge_state=service.knowledge_state,
        transcribed_answer=transcribed_answer,
        next_question_audio_base64=base64.b64encode(next_audio_bytes).decode("ascii"),
        next_question_audio_mime_type=next_audio_mime,
    )


@router.post("/{interview_id}/video-answers", response_model=VideoAnswerResponse)
def submit_video_answer(
    interview_id: str,
    turn_id: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> VideoAnswerResponse:
    """Transcribe a candidate's video answer and run it through the shared pipeline.

    This computes no behavioral/emotion signals -- see
    app.ai.video.provider.VideoAnalysisProvider for that (currently
    unimplemented) extension point.
    """
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    ensure_owner(interview.candidate.owner_user_id, current_user)

    video_bytes = file.file.read(MAX_VIDEO_ANSWER_BYTES + 1)
    if not video_bytes:
        raise HTTPException(status_code=422, detail="Uploaded video is empty")
    if len(video_bytes) > MAX_VIDEO_ANSWER_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded video is too large")
    mime_type = _base_mime_type(file.content_type)
    if mime_type not in ALLOWED_VIDEO_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Uploaded file must be a supported video format")

    voice_client = VoiceClient()
    try:
        transcribed_answer = voice_client.transcribe(video_bytes, mime_type)
    except (ValueError, RuntimeError) as exc:
        logger.warning("Transcription failed for interview %s: %s", interview_id, exc)
        raise HTTPException(
            status_code=502, detail="Failed to transcribe the recorded answer"
        ) from exc

    service, question = _execute_answer_turn(session, interview, turn_id, transcribed_answer)

    return VideoAnswerResponse(
        interview_id=interview.id,
        answered_turn=AnsweredTurnResponse(
            turn_id=service.last_answered_turn.id,
            turn_number=service.last_answered_turn.turn_number,
            question=service.last_answered_turn.question,
            answer=service.last_answered_turn.answer,
        ),
        answer_analysis=service.last_answer_analysis,
        evaluation=service.last_evaluation,
        interviewer_decision=service.last_decision,
        next_turn_id=service.current_turn_id,
        next_question=question,
        difficulty=service.difficulty,
        status=interview.status,
        knowledge_state=service.knowledge_state,
        transcribed_answer=transcribed_answer,
    )


@router.post("/{interview_id}/complete", response_model=InterviewStateResponse)
def complete_interview(
    interview_id: str,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewStateResponse:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    ensure_owner(interview.candidate.owner_user_id, current_user)
    if interview.status == INTERVIEW_STATUS_COMPLETED:
        raise HTTPException(status_code=409, detail="Interview has already been completed")
    if interview.status != INTERVIEW_STATUS_IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Interview cannot be completed from its current state")

    interview_repository.mark_completed(session, interview_id)

    service = InterviewTurnService.load(session, interview_id)
    turns = interview_repository.get_turns(session, interview_id)
    return InterviewStateResponse(
        interview_id=interview.id,
        candidate_id=interview.candidate_id,
        resume_id=interview.resume_id,
        objective=interview.objective,
        difficulty=service.difficulty,
        status=interview.status,
        current_question=service.current_question,
        knowledge_state=service.knowledge_state,
        turns=[InterviewTurnResponse.model_validate(turn) for turn in turns],
    )


@router.post("/{interview_id}/assessment", response_model=FinalAssessment)
def create_final_assessment(
    interview_id: str,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> FinalAssessment:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    ensure_owner(interview.candidate.owner_user_id, current_user)

    existing = assessment_repository.get_assessment(session, interview_id)
    if existing is not None:
        return FinalAssessment.model_validate(existing)

    if interview.status != INTERVIEW_STATUS_COMPLETED:
        raise HTTPException(
            status_code=409, detail="Interview must be completed before it can be assessed"
        )

    try:
        assessment = assessment_service.build_final_assessment(
            session, interview_id, interview.objective
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    row = assessment_repository.create_assessment(session, interview_id, assessment)
    return FinalAssessment.model_validate(row)


@router.get("/{interview_id}/assessment", response_model=FinalAssessment)
def get_final_assessment(
    interview_id: str,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> FinalAssessment:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    ensure_owner(interview.candidate.owner_user_id, current_user)

    existing = assessment_repository.get_assessment(session, interview_id)
    if existing is None:
        raise HTTPException(
            status_code=404, detail="No assessment has been generated for this interview yet"
        )
    return FinalAssessment.model_validate(existing)


@router.get("/{interview_id}", response_model=InterviewStateResponse)
def get_interview(
    interview_id: str,
    session: Session = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewStateResponse:
    interview = interview_repository.get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    ensure_owner(interview.candidate.owner_user_id, current_user)

    service = InterviewTurnService.load(session, interview_id)
    turns = interview_repository.get_turns(session, interview_id)
    return InterviewStateResponse(
        interview_id=interview.id,
        candidate_id=interview.candidate_id,
        resume_id=interview.resume_id,
        objective=interview.objective,
        difficulty=service.difficulty,
        status=interview.status,
        current_question=service.current_question,
        knowledge_state=service.knowledge_state,
        turns=[InterviewTurnResponse.model_validate(turn) for turn in turns],
    )
