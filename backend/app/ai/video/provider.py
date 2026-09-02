"""Extension point for future video-based behavioral analysis.

The current video interview pipeline only transcribes the candidate's spoken
answer (via the existing speech-to-text provider) and runs it through the
same interview turn pipeline used by the text and voice flows. It computes no
emotion, engagement, or attentiveness signals: there is no vetted model
integration for that in this project, and fabricating such scores would
violate the project's "do not fake functionality" constraint.

This interface defines the shape a future implementation would fill in, so
that capability can be added later without changing the interview pipeline
or its API contracts. No route currently constructs or calls a
VideoAnalysisProvider.
"""

from abc import ABC, abstractmethod

from app.schemas.video import VideoBehavioralSignals


class VideoAnalysisProvider(ABC):
    """Abstract interface for a future video behavioral analysis provider."""

    @abstractmethod
    def analyze(self, video_bytes: bytes, mime_type: str) -> VideoBehavioralSignals:
        """
        Analyze a candidate's video answer for behavioral signals.

        Args:
            video_bytes: Raw video file bytes
            mime_type: MIME type of the video (e.g. 'video/mp4')

        Returns:
            The behavioral signals a concrete provider is able to derive

        Raises:
            RuntimeError: If analysis fails
        """
