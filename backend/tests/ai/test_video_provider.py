"""Tests for the video analysis extension point.

VideoAnalysisProvider is intentionally unimplemented in this milestone (no
behavioral/emotion analysis is fabricated). These tests only verify the
abstract contract is well-formed and enforced, matching how the STT/TTS
abstractions in app.ai.voice.provider are tested.
"""

import pytest

from app.ai.video.provider import VideoAnalysisProvider
from app.schemas.video import VideoBehavioralSignals


def test_video_analysis_provider_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        VideoAnalysisProvider()


def test_a_concrete_provider_can_fulfill_the_contract():
    class StubVideoAnalysisProvider(VideoAnalysisProvider):
        def analyze(self, video_bytes: bytes, mime_type: str) -> VideoBehavioralSignals:
            return VideoBehavioralSignals(signals={}, notes=["stub"])

    provider = StubVideoAnalysisProvider()
    result = provider.analyze(b"fake-video-bytes", "video/mp4")

    assert isinstance(result, VideoBehavioralSignals)
    assert result.notes == ["stub"]


def test_video_behavioral_signals_defaults_are_empty():
    signals = VideoBehavioralSignals()

    assert signals.signals == {}
    assert signals.notes == []
