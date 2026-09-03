"""Voice interview schemas."""

from pydantic import BaseModel

from app.schemas.interview import InterviewAnswerResponse


class QuestionAudioResponse(BaseModel):
    """Synthesized audio for the interview's current pending question."""

    turn_id: str
    audio_base64: str
    audio_mime_type: str


class VoiceAnswerResponse(InterviewAnswerResponse):
    """Result of a voice interview answer submission.

    Carries everything a text answer submission does, plus the transcript of
    the spoken answer and synthesized audio for the next question. The audio
    fields are None when synthesis failed: the answer itself has already been
    evaluated and persisted at that point, so the turn is still valid and the
    client can fall back to the text of next_question (or retry
    GET /interviews/{id}/question-audio).
    """

    transcribed_answer: str
    next_question_audio_base64: str | None = None
    next_question_audio_mime_type: str | None = None
