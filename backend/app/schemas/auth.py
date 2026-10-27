"""Pydantic schemas for the authentication API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    # Plain password: never logged, never stored, never returned.
    password: str = Field(..., min_length=1, max_length=1024)


class SessionUser(BaseModel):
    """What the browser is allowed to know about the current session."""

    authenticated: bool
    username: str
    institution_id: int
    institution_name: str
    roles: List[str]


class LogoutResponse(BaseModel):
    status: str


class AuthErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
