"""Roster intake API routes."""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import (
    AuthContext,
    assert_institution_scope,
    get_scoped_batch,
    require_roles,
)
from app.config import settings
from app.db.session import get_db
from app.schemas.intake import (
    BatchConfirmRequest,
    BatchConfirmResponse,
    BatchCreateRequest,
    BatchCreateResponse,
    BatchListResponse,
    BatchReadResponse,
    BatchValidateResponse,
)
from app.services.auth import ROLE_NODAL, ROLE_OPERATOR
from app.services.roster import (
    RosterError,
    STATE_CREATED,
    STATE_SUBMITTED_FOR_REVIEW,
    STATE_VALIDATED,
    STATE_VALIDATION_FAILED,
    confirm_batch,
    create_batch,
    get_batch_summary,
    list_batch_summaries,
    validate_and_stage,
)

router = APIRouter(prefix="/api/v1/batches", tags=["batches"])

# Writing a roster is the Institution Data Operator's job (docs/PRD.md); the
# Nodal Officer reviews batches and may read them but must not upload.
OPERATOR = lambda: require_roles(ROLE_OPERATOR)  # noqa: E731
READER = lambda: require_roles(ROLE_OPERATOR, ROLE_NODAL)  # noqa: E731

_ERROR_STATUS_MAP = {
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "INVALID_STATE": status.HTTP_400_BAD_REQUEST,
    "INVALID_IDEMPOTENCY_KEY": status.HTTP_400_BAD_REQUEST,
    "IDEMPOTENCY_CONFLICT": status.HTTP_409_CONFLICT,
    "VALIDATION_FAILED": status.HTTP_400_BAD_REQUEST,
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "INVALID_FILE_TYPE": status.HTTP_400_BAD_REQUEST,
    "FILE_TOO_LARGE": status.HTTP_400_BAD_REQUEST,
    "EMPTY_FILE": status.HTTP_400_BAD_REQUEST,
    "INVALID_ENCODING": status.HTTP_400_BAD_REQUEST,
    "EMPTY_CSV": status.HTTP_400_BAD_REQUEST,
    "MISSING_HEADER": status.HTTP_400_BAD_REQUEST,
    "MISSING_COLUMNS": status.HTTP_400_BAD_REQUEST,
    "DUPLICATE_COLUMNS": status.HTTP_400_BAD_REQUEST,
}


def _scope_error_to_http(exc: RosterError) -> HTTPException:
    status_code = _ERROR_STATUS_MAP.get(exc.code, status.HTTP_400_BAD_REQUEST)
    return HTTPException(status_code=status_code, detail=exc.message)


@router.post("", response_model=BatchCreateResponse, status_code=status.HTTP_201_CREATED)
def create_intake_batch(
    request: BatchCreateRequest,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new intake batch in CREATED state.

    The institution comes from the session, not the request body: a body that
    names a different institution is refused.
    """
    assert_institution_scope(request.institution_id, auth)
    try:
        batch = create_batch(
            db=db,
            institution_id=auth.institution_id,
            academic_year=request.academic_year,
            checksum=request.checksum or "",
            schema_version=request.schema_version,
            idempotency_key=request.idempotency_key,
            uploader_ref=auth.username,
        )
    except RosterError as exc:
        raise _scope_error_to_http(exc) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error creating batch.",
        ) from exc
    return BatchCreateResponse(
        batch_id=batch.id,
        state=batch.state,
        idempotency_key=batch.idempotency_key,
        created_at=batch.created_at.isoformat() if batch.created_at else "",
    )


@router.post("/{batch_id}/validate", response_model=BatchValidateResponse)
def validate_intake_batch(
    batch_id: int,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR)),
    db: Session = Depends(get_db),
) -> Any:
    """Upload and validate a roster CSV.

    Stages every row - valid and invalid - without submitting anything; the
    batch must be confirmed explicitly.
    """
    get_scoped_batch(db, batch_id, auth)
    try:
        content = file.file.read()
        result = validate_and_stage(
            db=db,
            batch_id=batch_id,
            file_content=content,
            filename=file.filename or "upload.csv",
        )
    except RosterError as exc:
        raise _scope_error_to_http(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error validating batch.",
        ) from exc
    return BatchValidateResponse(**result)


@router.post("/{batch_id}/confirm", response_model=BatchConfirmResponse)
def confirm_intake_batch(
    batch_id: int,
    request: BatchConfirmRequest,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR)),
    db: Session = Depends(get_db),
) -> Any:
    """Explicitly confirm a validated batch.

    All-or-nothing: a batch with any invalid row is rejected. Retrying the
    same idempotency key returns the original outcome.
    """
    get_scoped_batch(db, batch_id, auth)
    try:
        result = confirm_batch(
            db=db,
            batch_id=batch_id,
            idempotency_key=request.idempotency_key,
        )
    except RosterError as exc:
        raise _scope_error_to_http(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error confirming batch.",
        ) from exc
    return BatchConfirmResponse(**result)


@router.get("", response_model=BatchListResponse)
def list_intake_batches(
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_NODAL)),
    db: Session = Depends(get_db),
) -> Any:
    """List the signed-in institution's batches, newest first.

    Scope comes from the session alone; there is no institution parameter to
    widen, and another institution's batches are never in the result set.
    """
    return list_batch_summaries(db, auth.institution_id)


@router.get("/{batch_id}", response_model=BatchReadResponse)
def read_intake_batch(
    batch_id: int,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_NODAL)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve batch status and summary (same institution only)."""
    get_scoped_batch(db, batch_id, auth)
    summary = get_batch_summary(db, batch_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found.",
        )
    return BatchReadResponse(**summary)
