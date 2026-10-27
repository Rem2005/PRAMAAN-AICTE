"""FastAPI dependencies: authentication, role checks, institution scope.

Authorization is decided here, server-side, from the session cookie. Client
fields such as `institution_id` in a request body are never trusted to grant
access; they may only ever match the scope already established by the session.
"""

from typing import Sequence

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.models import SubmissionBatch
from app.db.session import get_db
from app.services.auth import SESSION_COOKIE, AuthContext, resolve_session


def get_auth_context(
    request: Request, db: Session = Depends(get_db)
) -> AuthContext:
    """Resolve the session cookie into a validated server-side identity."""
    token = request.cookies.get(SESSION_COOKIE)
    context = resolve_session(db, token)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Sign in first.",
            headers={"WWW-Authenticate": 'Session realm="PRAMAAN-AICTE"'},
        )
    return context


def require_roles(*roles: str):
    """Deny-by-default guard: authenticated *and* holding one of `roles`."""

    def dependency(
        context: AuthContext = Depends(get_auth_context),
    ) -> AuthContext:
        if not context.has_any_role(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required role for this action.",
            )
        return context

    return dependency


def get_scoped_batch(
    db: Session, batch_id: int, context: AuthContext
) -> SubmissionBatch:
    """Load a batch only if it belongs to the caller's institution.

    A batch outside the caller's institution is reported as 404 rather than
    403 so the response does not confirm that some other institution's record
    exists (docs/frontend-design-system.md, section 7).
    """
    batch = db.get(SubmissionBatch, batch_id)
    if batch is None or batch.institution_id != context.institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found.",
        )
    return batch


def assert_institution_scope(requested_institution_id: int, context: AuthContext) -> None:
    """Reject a body that names an institution other than the caller's."""
    if requested_institution_id != context.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only create batches for your own institution.",
        )


__all__ = [
    "SESSION_COOKIE",
    "AuthContext",
    "Sequence",
    "assert_institution_scope",
    "get_auth_context",
    "get_scoped_batch",
    "require_roles",
]
