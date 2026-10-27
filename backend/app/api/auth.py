"""Authentication routes: login, logout, current identity."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Institution, User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LogoutResponse, SessionUser
from app.services.auth import (
    AuthContext,
    AuthError,
    SESSION_COOKIE,
    authenticate,
    create_session,
    revoke_session,
    roles_for_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_WWW_AUTH = {"WWW-Authenticate": 'Session realm="PRAMAAN-AICTE"'}


def _session_user(db: Session, user: User, roles: list[str]) -> SessionUser:
    institution = db.get(Institution, user.institution_id)
    return SessionUser(
        authenticated=True,
        username=user.username,
        institution_id=user.institution_id,
        institution_name=institution.name if institution else "",
        roles=sorted(roles),
    )


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,  # never readable from JavaScript
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/login", response_model=SessionUser)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)) -> Any:
    """Exchange a username and password for a server-side session cookie."""
    try:
        user = authenticate(db, request.username, request.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers=_WWW_AUTH,
        ) from exc

    token = create_session(db, user)
    _set_session_cookie(response, token)
    return _session_user(db, user, roles_for_user(db, user))


@router.post("/logout", response_model=LogoutResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Any:
    """Revoke the current session server-side and clear the cookie."""
    revoke_session(db, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return LogoutResponse(status="signed_out")


@router.get("/me", response_model=SessionUser)
def me(request: Request, db: Session = Depends(get_db)) -> Any:
    """Describe the current session, or report that there is none."""
    context = resolve_or_none(request, db)
    if context is None:
        return SessionUser(
            authenticated=False,
            username="",
            institution_id=0,
            institution_name="",
            roles=[],
        )
    user = db.get(User, context.user_id)
    if user is None:
        return SessionUser(
            authenticated=False,
            username="",
            institution_id=0,
            institution_name="",
            roles=[],
        )
    return _session_user(db, user, sorted(context.roles))


def resolve_or_none(request: Request, db: Session) -> "AuthContext | None":
    from app.services.auth import resolve_session

    return resolve_session(db, request.cookies.get(SESSION_COOKIE))
