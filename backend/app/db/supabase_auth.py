"""Supabase Auth (GoTrue) REST client for signup, login, logout, and token verification.

Mirrors app/db/storage.py's approach: talk to Supabase's REST API directly over
httpx (already a dependency) rather than adding the full supabase-py SDK. All
password handling, token issuance, and token verification is delegated entirely
to Supabase Auth -- this module never sees or stores a password beyond the single
outgoing request, and never implements its own session/token logic.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import SUPABASE_ANON_KEY, SUPABASE_URL


class SupabaseAuthError(Exception):
    """Raised when a Supabase Auth request fails or Auth is not configured."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class AuthSession:
    access_token: str
    refresh_token: str
    user_id: str
    email: str | None


@dataclass
class SignUpResult:
    user_id: str
    email: str | None
    session: AuthSession | None  # None when Supabase requires email confirmation first


@dataclass
class AuthenticatedUser:
    id: str
    email: str | None
    access_token: str


def _require_configured() -> str:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise SupabaseAuthError(503, "Supabase Auth is not configured.")
    return f"{SUPABASE_URL}/auth/v1"


def _headers(access_token: str | None = None) -> dict[str, str]:
    headers = {"apikey": SUPABASE_ANON_KEY or "", "Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "Authentication request failed."
    return body.get("error_description") or body.get("msg") or body.get("error") or "Authentication request failed."


def _request(method: str, url: str, **kwargs) -> httpx.Response:
    try:
        response = httpx.request(method, url, timeout=15, **kwargs)
    except httpx.HTTPError as exc:
        raise SupabaseAuthError(502, f"Failed to reach Supabase Auth: {exc}") from exc
    if response.status_code >= 400:
        raise SupabaseAuthError(response.status_code, _error_message(response))
    return response


def _session_from_payload(body: dict) -> AuthSession | None:
    access_token = body.get("access_token")
    if not access_token:
        return None
    user = body.get("user") or {}
    return AuthSession(
        access_token=access_token,
        refresh_token=body.get("refresh_token", ""),
        user_id=user.get("id", ""),
        email=user.get("email"),
    )


def sign_up(email: str, password: str) -> SignUpResult:
    """Create a new Supabase Auth user. session is None if email confirmation is required."""
    base_url = _require_configured()
    response = _request(
        "POST", f"{base_url}/signup", headers=_headers(), json={"email": email, "password": password}
    )
    body = response.json()
    user = body.get("user") or body  # signup may return the user object directly
    session = _session_from_payload(body)
    return SignUpResult(user_id=user.get("id", ""), email=user.get("email"), session=session)


def sign_in(email: str, password: str) -> AuthSession:
    """Log in an existing Supabase Auth user with email/password."""
    base_url = _require_configured()
    response = _request(
        "POST",
        f"{base_url}/token?grant_type=password",
        headers=_headers(),
        json={"email": email, "password": password},
    )
    session = _session_from_payload(response.json())
    if session is None:
        raise SupabaseAuthError(401, "Invalid email or password.")
    return session


def sign_out(access_token: str) -> None:
    """Revoke a session. Best-effort: the token will simply expire otherwise."""
    try:
        base_url = _require_configured()
    except SupabaseAuthError:
        return
    try:
        httpx.post(f"{base_url}/logout", headers=_headers(access_token), timeout=15)
    except httpx.HTTPError:
        pass


def get_user(access_token: str) -> AuthenticatedUser:
    """Resolve the authenticated user for a bearer token, or raise if invalid/expired."""
    base_url = _require_configured()
    response = _request("GET", f"{base_url}/user", headers=_headers(access_token))
    body = response.json()
    return AuthenticatedUser(id=body["id"], email=body.get("email"), access_token=access_token)
