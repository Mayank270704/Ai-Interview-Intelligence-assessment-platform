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
