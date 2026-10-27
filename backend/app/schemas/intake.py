"""Pydantic request/response schemas for the roster intake API."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class BatchCreateRequest(BaseModel):
    institution_id: int = Field(..., gt=0)
    academic_year: str = Field(..., min_length=1, max_length=32)
    # Optional: a client that knows the file's SHA-256 up front may declare it;
    # the server always recomputes the checksum from the uploaded bytes.
    checksum: Optional[str] = Field(None, max_length=128)
    schema_version: str = Field(..., min_length=1, max_length=64)
    # Optional client-supplied key so a retried create returns the original
    # batch instead of creating a duplicate.
    idempotency_key: Optional[str] = Field(None, min_length=1, max_length=128)


class BatchCreateResponse(BaseModel):
    batch_id: int
    state: str
    idempotency_key: str
    created_at: str


class RowValidationResult(BaseModel):
    row_number: int
    local_ref: Optional[str] = None
    valid: bool
    errors: List[str] = []


class BatchValidateResponse(BaseModel):
    batch_id: int
    state: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    rows: List[RowValidationResult]


class BatchConfirmRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class BatchConfirmResponse(BaseModel):
    batch_id: int
    state: str
    persisted_count: int


class BatchListItem(BaseModel):
    batch_id: int
    state: str
    academic_year: str
    # NULL until the batch has been uploaded (or for batches created before
    # the file name was recorded).
    source_filename: Optional[str] = None
    uploader_ref: str
    created_at: str
    total_rows: int
    valid_rows: int
    invalid_rows: int


class BatchListTotals(BaseModel):
    batches: int
    total_rows: int
    valid_rows: int
    invalid_rows: int


class BatchListResponse(BaseModel):
    batches: List[BatchListItem]
    totals: BatchListTotals


class BatchReadResponse(BaseModel):
    batch_id: int
    institution_id: int
    state: str
    academic_year: str
    checksum: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    created_at: str
    submitted_at: Optional[str] = None
