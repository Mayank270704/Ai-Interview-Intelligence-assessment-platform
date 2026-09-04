import os

import pytest

APP_NAME = os.getenv("APP_NAME", "AI Interview Intelligence API")


@pytest.fixture(autouse=True)
def reset_auth_rate_limits():
    """Keep the auth rate limiters from leaking state between tests.

    The limiters are module-level singletons keyed by client address, and every
    test client shares one address, so without this a test's attempts would
    count against an unrelated later test.
    """
    from app.api.v1.auth import login_limiter, signup_limiter

    login_limiter.reset()
    signup_limiter.reset()
    yield
    login_limiter.reset()
    signup_limiter.reset()


@pytest.fixture(autouse=True)
def reset_gemini_clients():
    """Drop the process-wide Gemini client cache between tests.

    The cache is keyed by API key and deliberately outlives a request, so a
    client built while `genai.Client` was patched would otherwise be handed to
    the next test instead of its own mock.
    """
    from app.ai.llm.gemini_provider import shared_client

    shared_client.cache_clear()
    yield
    shared_client.cache_clear()
