"""Video interview schemas."""

from pydantic import BaseModel, Field

from app.schemas.interview import InterviewAnswerResponse


class VideoBehavioralSignals(BaseModel):
    """Extension-point shape for future video-based behavioral analysis.

    Deliberately unpopulated by the current pipeline: no milestone of this
    project claims to detect emotion, engagement, or eye contact from video,
    and this schema is never instantiated with fabricated data. It exists so
    a future `VideoAnalysisProvider` implementation (see
    app.ai.video.provider) has an agreed-upon output shape to fill in.
    """

    signals: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class VideoAnswerResponse(InterviewAnswerResponse):
    """Result of a video interview answer submission.

    Carries everything a text answer submission does, plus the transcript of
    the candidate's spoken answer. No behavioral or emotional signals are
    computed here -- see app.ai.video.provider.VideoAnalysisProvider for the
    documented (currently unimplemented) extension point.
    """

    transcribed_answer: str
