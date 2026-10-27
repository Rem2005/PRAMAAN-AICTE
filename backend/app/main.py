from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.intake import router as intake_router
from app.api.reconciliation import router as reconciliation_router
from app.config import settings

app = FastAPI(title=settings.app_name, version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    # Session cookies are only ever sent when the origin is explicitly listed;
    # credentials are required for cookie-based authentication to work at all.
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # Enumerated rather than "*": browsers reject a wildcard allow-headers
    # on a credentialed preflight request.
    allow_headers=["Content-Type"],
)

app.include_router(auth_router)
app.include_router(intake_router)
app.include_router(reconciliation_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Basic liveness check for the application foundation milestone."""
    return {"status": "ok"}
