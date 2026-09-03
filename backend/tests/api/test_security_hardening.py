"""Tests for the production-hardening pass: rate limiting, CORS, and error leakage."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth import login_limiter, signup_limiter
from app.core.rate_limit import RateLimiter
from app.db import supabase_auth
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Rate limiter unit behaviour
# ---------------------------------------------------------------------------


def test_rate_limiter_allows_requests_up_to_the_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)

    for _ in range(3):
        limiter.check("client-a")


def test_rate_limiter_blocks_past_the_limit():
    from fastapi import HTTPException

    limiter = RateLimiter(max_requests=2, window_seconds=60)
    limiter.check("client-a")
    limiter.check("client-a")

    with pytest.raises(HTTPException) as exc_info:
        limiter.check("client-a")

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers is not None
    assert "Retry-After" in exc_info.value.headers


def test_rate_limiter_isolates_clients():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check("client-a")

    limiter.check("client-b")


def test_rate_limiter_window_expiry_allows_new_requests():
    limiter = RateLimiter(max_requests=1, window_seconds=0.05)
    limiter.check("client-a")

    import time

    time.sleep(0.06)
    limiter.check("client-a")


def test_rate_limiter_reset_clears_counters():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check("client-a")

    limiter.reset()

    limiter.check("client-a")


# ---------------------------------------------------------------------------
# Rate limiting on the credential endpoints
# ---------------------------------------------------------------------------


def test_repeated_failed_logins_are_rate_limited(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "sign_in",
        MagicMock(side_effect=supabase_auth.SupabaseAuthError(401, "Invalid email or password.")),
    )
    payload = {"email": "jane@example.com", "password": "wrong-password"}

    statuses = [client.post("/api/v1/auth/login", json=payload).status_code for _ in range(12)]

    assert statuses[0] == 401
    assert 429 in statuses, "brute-force attempts should eventually be rate limited"
    assert statuses[-1] == 429


def test_login_rate_limit_response_carries_retry_after(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "sign_in",
        MagicMock(side_effect=supabase_auth.SupabaseAuthError(401, "Invalid email or password.")),
    )
    payload = {"email": "jane@example.com", "password": "wrong-password"}

    last = None
    for _ in range(12):
        last = client.post("/api/v1/auth/login", json=payload)

    assert last is not None
    assert last.status_code == 429
    assert "retry-after" in {key.lower() for key in last.headers}


def test_repeated_signups_are_rate_limited(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "sign_up",
        MagicMock(return_value=supabase_auth.SignUpResult(user_id="u", email="e", session=None)),
    )
    payload = {"email": "jane@example.com", "password": "password123"}

    statuses = [client.post("/api/v1/auth/signup", json=payload).status_code for _ in range(8)]

    assert statuses[0] == 200
    assert statuses[-1] == 429


def test_limiters_are_independent(client: TestClient, monkeypatch):
    """Exhausting signup attempts must not lock a user out of logging in."""
    monkeypatch.setattr(
        supabase_auth,
        "sign_up",
        MagicMock(return_value=supabase_auth.SignUpResult(user_id="u", email="e", session=None)),
    )
    monkeypatch.setattr(
        supabase_auth,
        "sign_in",
        MagicMock(
            return_value=supabase_auth.AuthSession(
                access_token="t", refresh_token="r", user_id="u", email="e"
            )
        ),
    )
    for _ in range(8):
        client.post("/api/v1/auth/signup", json={"email": "a@example.com", "password": "password123"})

    response = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})

    assert response.status_code == 200


def test_rate_limiters_are_reset_between_tests():
    """The autouse conftest fixture must hand each test clean limiters."""
    assert login_limiter is not None
    assert signup_limiter is not None
    for _ in range(10):
        login_limiter.check("fresh-client")


# ---------------------------------------------------------------------------
# Error leakage
# ---------------------------------------------------------------------------


def test_upstream_auth_failure_is_not_relayed_to_the_client(client: TestClient, monkeypatch):
    """A 500 from Supabase must not leak its internals into our response body."""
    monkeypatch.setattr(
        supabase_auth,
        "sign_in",
        MagicMock(
            side_effect=supabase_auth.SupabaseAuthError(
                500, "internal db error at postgres://user:secret@host/db"
            )
        ),
    )

    response = client.post(
        "/api/v1/auth/login", json={"email": "jane@example.com", "password": "password123"}
    )

    assert response.status_code == 502
    assert "secret" not in response.text
    assert response.json()["detail"] == "Authentication service is currently unavailable"


def test_invalid_token_response_does_not_echo_upstream_detail(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "get_user",
        MagicMock(side_effect=supabase_auth.SupabaseAuthError(401, "jwt malformed: eyJhbGciOi...")),
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})

    assert response.status_code == 401
    assert "eyJhbGciOi" not in response.text
    assert response.json()["detail"] == "Invalid or expired credentials"


def test_token_verification_outage_is_not_relayed(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "get_user",
        MagicMock(side_effect=supabase_auth.SupabaseAuthError(500, "upstream stack trace")),
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer token"})

    assert response.status_code == 502
    assert "stack trace" not in response.text


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_cors_allows_the_configured_frontend_origin(client: TestClient):
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_does_not_allow_an_unlisted_origin(client: TestClient):
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.example.com"})

    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"


def test_cors_origins_are_configurable_and_not_a_wildcard():
    from app.core.config import CORS_ALLOW_ORIGINS

    assert "*" not in CORS_ALLOW_ORIGINS
    assert all(origin.startswith("http") for origin in CORS_ALLOW_ORIGINS)


# ---------------------------------------------------------------------------
# Authentication coverage
# ---------------------------------------------------------------------------


def dep_names(dependencies, out: list[str]) -> None:
    """Collect dependency callable names depth-first, in resolution order."""
    for dependency in dependencies:
        if dependency.call is not None:
            out.append(getattr(dependency.call, "__name__", type(dependency.call).__name__))
        dep_names(dependency.dependencies, out)


def endpoints_under_test():
    """Every route with a dependency tree, flattening FastAPI's nested routers.

    FastAPI >=0.141 keeps included routers nested instead of flattening their
    routes onto the app, so expand them when the app exposes them.
    """
    for route in app.routes:
        expand = getattr(route, "effective_candidates", None)
        for candidate in expand() if expand is not None else [route]:
            if getattr(candidate, "dependant", None) is not None:
                yield candidate


def _route_auth_map() -> dict[tuple[str, str], bool]:
    """Map (method, path) -> whether the route requires an authenticated user."""
    routes: dict[tuple[str, str], bool] = {}
    for route in endpoints_under_test():
        path = getattr(route, "path", "")
        if not path.startswith("/api/"):
            continue
        names: list[str] = []
        dep_names(route.dependant.dependencies, names)
        for method in set(getattr(route, "methods", [])) - {"HEAD", "OPTIONS"}:
            routes[(method, path)] = "get_current_user" in names
    return routes


def test_only_health_and_credential_endpoints_are_public():
    """Every route except health/login/signup must require authentication."""
    expected_public = {
        ("GET", "/api/v1/health"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/signup"),
    }

    routes = _route_auth_map()
    actual_public = {route for route, protected in routes.items() if not protected}

    assert actual_public == expected_public, (
        "unexpected public routes: "
        f"{sorted(actual_public - expected_public)}; "
        f"unexpectedly protected: {sorted(expected_public - actual_public)}"
    )


def test_authentication_is_resolved_before_the_database_session():
    """An unauthenticated request must be rejected without opening a transaction.

    FastAPI resolves a route's dependencies in signature order, so get_current_user
    has to come first -- otherwise anonymous traffic opens a database session (and
    a 401 turns into a 500 whenever the database is unreachable).
    """
    offenders = []
    for route in endpoints_under_test():
        path = getattr(route, "path", "")
        if not path.startswith("/api/"):
            continue
        names: list[str] = []
        dep_names(route.dependant.dependencies, names)
        if "get_current_user" not in names or "get_session" not in names:
            continue
        if names.index("get_session") < names.index("get_current_user"):
            offenders.append(path)

    assert offenders == [], f"database session resolved before authentication on: {offenders}"


def test_every_interview_and_resume_route_is_protected():
    routes = _route_auth_map()

    unprotected = [
        route
        for route, protected in routes.items()
        if not protected and ("/interviews" in route[1] or "/resumes" in route[1] or "/candidates" in route[1])
    ]

    assert unprotected == []
