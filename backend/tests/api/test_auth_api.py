"""API tests for authentication routes. All Supabase Auth calls are mocked."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db import supabase_auth
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_signup_returns_session_when_no_email_confirmation_required(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "sign_up",
        MagicMock(
            return_value=supabase_auth.SignUpResult(
                user_id="user-1",
                email="jane@example.com",
                session=supabase_auth.AuthSession(
                    access_token="token-abc", refresh_token="refresh-abc", user_id="user-1", email="jane@example.com"
                ),
            )
        ),
    )

    response = client.post("/api/v1/auth/signup", json={"email": "jane@example.com", "password": "password123"})

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user-1"
    assert body["email_confirmation_required"] is False
    assert body["session"]["access_token"] == "token-abc"


def test_signup_reports_email_confirmation_required(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "sign_up",
        MagicMock(return_value=supabase_auth.SignUpResult(user_id="user-1", email="jane@example.com", session=None)),
    )

    response = client.post("/api/v1/auth/signup", json={"email": "jane@example.com", "password": "password123"})

    assert response.status_code == 200
    body = response.json()
    assert body["email_confirmation_required"] is True
    assert body["session"] is None


def test_signup_rejects_short_password(client: TestClient):
    response = client.post("/api/v1/auth/signup", json={"email": "jane@example.com", "password": "short"})

    assert response.status_code == 422


def test_signup_with_existing_email_returns_the_upstream_status(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "sign_up",
        MagicMock(side_effect=supabase_auth.SupabaseAuthError(400, "User already registered")),
    )

    response = client.post("/api/v1/auth/signup", json={"email": "jane@example.com", "password": "password123"})

    assert response.status_code == 400


def test_signup_when_auth_not_configured_returns_503(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth, "sign_up", MagicMock(side_effect=supabase_auth.SupabaseAuthError(503, "Supabase Auth is not configured."))
    )

    response = client.post("/api/v1/auth/signup", json={"email": "jane@example.com", "password": "password123"})

    assert response.status_code == 503


def test_login_returns_session(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "sign_in",
        MagicMock(
            return_value=supabase_auth.AuthSession(
                access_token="token-abc", refresh_token="refresh-abc", user_id="user-1", email="jane@example.com"
            )
        ),
    )

    response = client.post("/api/v1/auth/login", json={"email": "jane@example.com", "password": "password123"})

    assert response.status_code == 200
    assert response.json()["access_token"] == "token-abc"


def test_login_with_invalid_credentials_returns_401(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "sign_in",
        MagicMock(side_effect=supabase_auth.SupabaseAuthError(401, "Invalid email or password.")),
    )

    response = client.post("/api/v1/auth/login", json={"email": "jane@example.com", "password": "wrong"})

    assert response.status_code == 401


def test_me_requires_authentication(client: TestClient):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_rejects_malformed_bearer_token(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth, "get_user", MagicMock(side_effect=supabase_auth.SupabaseAuthError(401, "invalid JWT"))
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})

    assert response.status_code == 401


def test_me_returns_the_authenticated_user(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "get_user",
        MagicMock(
            return_value=supabase_auth.AuthenticatedUser(
                id="user-1", email="jane@example.com", access_token="token-abc"
            )
        ),
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer token-abc"})

    assert response.status_code == 200
    assert response.json() == {"id": "user-1", "email": "jane@example.com"}


def test_logout_requires_authentication(client: TestClient):
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 401


def test_logout_succeeds_with_a_valid_token(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "get_user",
        MagicMock(
            return_value=supabase_auth.AuthenticatedUser(
                id="user-1", email="jane@example.com", access_token="token-abc"
            )
        ),
    )
    sign_out = MagicMock()
    monkeypatch.setattr(supabase_auth, "sign_out", sign_out)

    response = client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer token-abc"})

    assert response.status_code == 204
    sign_out.assert_called_once_with("token-abc")


def test_health_endpoint_remains_unauthenticated(client: TestClient):
    """Auth must not break endpoints that are genuinely meant to stay public."""
    assert client.get("/api/v1/health").status_code == 200


def test_candidates_endpoint_requires_authentication(client: TestClient):
    """Ownership was added in Milestone 3: candidate creation now requires a bearer token."""
    response = client.post("/api/v1/candidates", json={"full_name": "Jane Doe"})

    assert response.status_code == 401
