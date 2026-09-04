"""Authentication API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.rate_limit import RateLimiter, client_key
from app.core.security import get_current_user
from app.db import supabase_auth
from app.db.supabase_auth import AuthenticatedUser, SupabaseAuthError
from app.schemas.auth import (
    AuthSessionResponse,
    CurrentUserResponse,
    LoginRequest,
    SignUpRequest,
    SignUpResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Credential endpoints are the brute-force surface, so they carry their own
# per-client limits (see app.core.rate_limit for this limiter's scope).
login_limiter = RateLimiter(max_requests=10, window_seconds=300)
signup_limiter = RateLimiter(max_requests=5, window_seconds=900)


def _map_auth_error(exc: SupabaseAuthError) -> HTTPException:
    # 429 is Supabase's own limit (notably its confirmation-email quota), which
    # is a separate ceiling from this API's per-client limiter. Relaying it as
    # 502 would tell the caller the service is broken when in fact they only
    # need to wait, and would hide a retryable condition behind a generic error.
    if exc.status_code == 429:
        return HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait and try again.",
            headers={"Retry-After": "60"},
        )
    if exc.status_code in (400, 401, 403, 422, 503):
        return HTTPException(status_code=exc.status_code, detail=str(exc))
    logger.warning("Supabase Auth request failed with status %s: %s", exc.status_code, exc)
    return HTTPException(status_code=502, detail="Authentication service is currently unavailable")


@router.post("/signup", response_model=SignUpResponse)
def signup(request: SignUpRequest, http_request: Request) -> SignUpResponse:
    signup_limiter.check(client_key(http_request))

    try:
        result = supabase_auth.sign_up(request.email, request.password)
    except SupabaseAuthError as exc:
        raise _map_auth_error(exc) from exc

    return SignUpResponse(
        user_id=result.user_id,
        email=result.email,
        email_confirmation_required=result.session is None,
        session=(
            AuthSessionResponse(
                access_token=result.session.access_token,
                refresh_token=result.session.refresh_token,
                user_id=result.session.user_id,
                email=result.session.email,
            )
            if result.session
            else None
        ),
    )


@router.post("/login", response_model=AuthSessionResponse)
def login(request: LoginRequest, http_request: Request) -> AuthSessionResponse:
    login_limiter.check(client_key(http_request))

    try:
        session = supabase_auth.sign_in(request.email, request.password)
    except SupabaseAuthError as exc:
        raise _map_auth_error(exc) from exc

    return AuthSessionResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user_id=session.user_id,
        email=session.email,
    )


@router.post("/logout", status_code=204)
def logout(current_user: AuthenticatedUser = Depends(get_current_user)) -> None:
    supabase_auth.sign_out(current_user.access_token)


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: AuthenticatedUser = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(id=current_user.id, email=current_user.email)
