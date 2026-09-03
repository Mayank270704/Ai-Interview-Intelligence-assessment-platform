"""Live Gemini connectivity check.

Unlike the rest of the suite, this test calls the real Gemini API: it verifies
credentials and reachability, not application logic. It is therefore opt-in --
set RUN_LIVE_LLM_TESTS=1 with a working GEMINI_API_KEY to run it -- so that a
missing key, a quota limit, or an outage cannot be mistaken for a code failure
in the deterministic suite. Every other LLM-dependent test mocks the provider.
"""

import os

import pytest

from app.ai.llm.client import LLMClient

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="Live Gemini test; set RUN_LIVE_LLM_TESTS=1 to run it against the real API.",
)


def test_gemini_connection():
    client = LLMClient()
    response = client.generate("Reply with exactly: Gemini connection successful")

    assert response.strip() == "Gemini connection successful"
