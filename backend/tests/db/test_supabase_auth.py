"""Tests for the Supabase Auth REST client. All Supabase calls are mocked."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.db import supabase_auth as auth


def _configure(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(auth, "SUPABASE_ANON_KEY", "anon-key")


def _response(status_code: int, json_body: dict) -> MagicMock:
    response = MagicMock(status_code=status_code)
    response.json.return_value = json_body
    return response


def test_sign_up_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_URL", None)
    monkeypatch.setattr(auth, "SUPABASE_ANON_KEY", None)

    with pytest.raises(auth.SupabaseAuthError) as exc_info:
        auth.sign_up("jane@example.com", "password123")
    assert exc_info.value.status_code == 503


def test_sign_up_returns_session_when_email_confirmation_not_required(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(
        httpx,
        "request",
        MagicMock(
            return_value=_response(
                200,
                {
                    "access_token": "token-abc",
                    "refresh_token": "refresh-abc",
                    "user": {"id": "user-1", "email": "jane@example.com"},
                },
            )
        ),
    )

    result = auth.sign_up("jane@example.com", "password123")

    assert result.user_id == "user-1"
    assert result.session is not None
    assert result.session.access_token == "token-abc"


def test_sign_up_requires_email_confirmation_when_no_session_issued(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(
        httpx,
        "request",
        MagicMock(return_value=_response(200, {"id": "user-1", "email": "jane@example.com"})),
    )

    result = auth.sign_up("jane@example.com", "password123")

    assert result.user_id == "user-1"
    assert result.session is None


def test_sign_up_raises_on_error_response(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(
        httpx,
        "request",
        MagicMock(return_value=_response(400, {"error_description": "User already registered"})),
    )

    with pytest.raises(auth.SupabaseAuthError) as exc_info:
        auth.sign_up("jane@example.com", "password123")
    assert exc_info.value.status_code == 400
    assert "already registered" in str(exc_info.value)


def test_sign_in_returns_session(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(
        httpx,
        "request",
        MagicMock(
            return_value=_response(
                200,
                {
                    "access_token": "token-abc",
                    "refresh_token": "refresh-abc",
                    "user": {"id": "user-1", "email": "jane@example.com"},
                },
            )
        ),
    )

    session = auth.sign_in("jane@example.com", "password123")

    assert session.access_token == "token-abc"
    assert session.user_id == "user-1"


def test_sign_in_with_invalid_credentials_raises(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(
        httpx,
        "request",
        MagicMock(return_value=_response(400, {"error_description": "Invalid login credentials"})),
    )

    with pytest.raises(auth.SupabaseAuthError) as exc_info:
        auth.sign_in("jane@example.com", "wrong-password")
    assert exc_info.value.status_code == 400


def test_sign_in_network_failure_raises_502(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(httpx, "request", MagicMock(side_effect=httpx.ConnectTimeout("timed out")))

    with pytest.raises(auth.SupabaseAuthError) as exc_info:
        auth.sign_in("jane@example.com", "password123")
    assert exc_info.value.status_code == 502


def test_get_user_returns_authenticated_user(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(
        httpx, "request", MagicMock(return_value=_response(200, {"id": "user-1", "email": "jane@example.com"}))
    )

    user = auth.get_user("token-abc")

    assert user.id == "user-1"
    assert user.email == "jane@example.com"
    assert user.access_token == "token-abc"


def test_get_user_with_invalid_token_raises(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(
        httpx, "request", MagicMock(return_value=_response(401, {"msg": "invalid JWT"}))
    )

    with pytest.raises(auth.SupabaseAuthError) as exc_info:
        auth.get_user("bad-token")
    assert exc_info.value.status_code == 401


def test_sign_out_is_best_effort_and_never_raises_on_network_error(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(httpx, "post", MagicMock(side_effect=httpx.ConnectTimeout("timed out")))

    auth.sign_out("token-abc")  # must not raise


def test_sign_out_is_a_noop_when_not_configured(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_URL", None)
    monkeypatch.setattr(auth, "SUPABASE_ANON_KEY", None)
    post = MagicMock()
    monkeypatch.setattr(httpx, "post", post)

    auth.sign_out("token-abc")

    post.assert_not_called()
