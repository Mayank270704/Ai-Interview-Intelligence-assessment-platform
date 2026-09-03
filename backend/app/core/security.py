"""Authentication and security utilities."""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import supabase_auth
from app.db.supabase_auth import AuthenticatedUser, SupabaseAuthError

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """FastAPI dependency: resolve the authenticated user from the request's bearer token.

    Delegates verification to Supabase Auth itself (no local JWT parsing/secret
    management here) -- raises 401 for a missing/invalid/expired token, or 503 if
    Supabase Auth is not configured in this environment.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        return supabase_auth.get_user(credentials.credentials)
    except SupabaseAuthError as exc:
        if exc.status_code == 503:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if exc.status_code in (401, 403, 404):
            raise HTTPException(status_code=401, detail="Invalid or expired credentials") from exc
        # Upstream failure: log the detail, but don't relay it to the caller.
        logger.warning("Token verification failed with status %s: %s", exc.status_code, exc)
        raise HTTPException(
            status_code=502, detail="Authentication service is currently unavailable"
        ) from exc


def ensure_owner(owner_user_id: str | None, current_user: AuthenticatedUser) -> None:
    """Enforce that the current user owns a resource, without revealing whether a
    resource merely owned by someone else exists (returns 404, not 403, on mismatch
    -- an ID belonging to another user should look identical to a nonexistent ID).

    An unowned resource (a legacy row predating candidate ownership) belongs to
    nobody and is never matchable, so an absent owner is rejected outright rather
    than compared -- otherwise an identity that somehow carried an empty id would
    match every one of those rows.
    """
    if not owner_user_id or not current_user.id or owner_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resource not found")
