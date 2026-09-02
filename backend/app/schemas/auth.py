"""Authentication schemas."""

from pydantic import BaseModel, Field


class SignUpRequest(BaseModel):
    """Request body for creating a new account."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Request body for logging in with an existing account."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class AuthSessionResponse(BaseModel):
    """An issued Supabase Auth session."""

    access_token: str
    refresh_token: str
    user_id: str
    email: str | None = None


class SignUpResponse(BaseModel):
    """Result of a signup request. session is omitted when email confirmation is required."""

    user_id: str
    email: str | None = None
    email_confirmation_required: bool
    session: AuthSessionResponse | None = None


class CurrentUserResponse(BaseModel):
    """The authenticated user resolved from the request's bearer token."""

    id: str
    email: str | None = None
