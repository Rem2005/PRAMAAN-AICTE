"""Local authentication: password hashing and server-side sessions.

Mechanism choice (Milestone 6)
------------------------------
`docs/architecture.md` requires "session, role, institution scope" but does not
name a provider, and no official identity provider is available to this
prototype: the external verification gates in `docs/research-and-verification.md`
are still open, and inventing an official integration is forbidden (AGENTS.md
strict directive 13).

Options considered:

1. External OIDC/SAML identity provider - rejected. Requires an official
   contract, credentials and sandbox access we do not have.
2. Self-contained JWT bearer tokens - rejected. Needs a new dependency, puts
   verification material in browser storage, and makes the session-revocation
   control required by `docs/security-privacy.md` harder to implement honestly.
3. Opaque server-side session in an HttpOnly cookie - chosen. Standard library
   only, the database is the single source of truth, and revocation is a row
   update. The cookie is HttpOnly so it is never readable from JavaScript,
   which keeps it out of client logs and analytics.

Passwords are stored as PBKDF2-HMAC-SHA256 using `hashlib.pbkdf2_hmac` (a
standard, documented KDF), encoded as
`pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`. The work factor is a
configurable engineering parameter, not a compliance claim. An empty stored
hash can never verify.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import AuthSession, Institution, User, UserRoleAssignment

SESSION_COOKIE = "pramaan_session"

# Roles from docs/PRD.md. Stored verbatim in user_role_assignments.role.
ROLE_OPERATOR = "INSTITUTION_DATA_OPERATOR"
ROLE_NODAL = "NODAL_OFFICER"
ROLE_IDENTITY_REVIEW = "IDENTITY_REVIEW_OFFICER"
ROLE_POLICY_AUTHOR = "POLICY_AUTHOR"
ROLE_POLICY_APPROVER = "POLICY_APPROVER"
ROLE_VERIFICATION_REQUESTER = "VERIFICATION_REQUESTER"
ROLE_AUDITOR = "AUDITOR"
ROLE_ADMIN = "PLATFORM_ADMIN"

PASSWORD_SCHEME = "pbkdf2_sha256"
_SALT_BYTES = 16
_TOKEN_BYTES = 32


class AuthError(Exception):
    """Raised for local account and session problems."""

    def __init__(self, message: str, code: str = "AUTHN_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AuthContext:
    """Validated server-side identity. Never built from client-supplied fields."""

    user_id: int
    username: str
    institution_id: int
    roles: frozenset

    def has_any_role(self, roles: Sequence[str]) -> bool:
        return bool(set(roles) & set(self.roles))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str, iterations: Optional[int] = None) -> str:
    """Encode a password with PBKDF2-HMAC-SHA256."""
    if iterations is None:
        iterations = settings.password_hash_iterations
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{PASSWORD_SCHEME}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time password check. Fails closed on any malformed input."""
    if not password or not encoded:
        return False
    parts = encoded.split("$")
    if len(parts) != 4 or parts[0] != PASSWORD_SCHEME:
        return False
    try:
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected = bytes.fromhex(parts[3])
    except ValueError:
        return False
    if iterations <= 0 or not salt or not expected:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def roles_for_user(db: Session, user: User) -> List[str]:
    """Active, institution-scoped roles for a user."""
    rows = db.execute(
        select(UserRoleAssignment.role).where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.institution_id == user.institution_id,
            UserRoleAssignment.status == "ACTIVE",
        )
    ).all()
    return sorted({row[0] for row in rows})


def create_user(
    db: Session,
    username: str,
    password: str,
    institution_id: int,
    roles: Iterable[str],
) -> User:
    """Create a local account with the given institution-scoped roles."""
    username = username.strip()
    if not username:
        raise AuthError("Username is required.", code="VALIDATION_ERROR")
    if not password:
        raise AuthError("Password is required.", code="VALIDATION_ERROR")

    institution = db.get(Institution, institution_id)
    if not institution:
        raise AuthError(
            f"Institution {institution_id} not found.", code="NOT_FOUND"
        )

    existing = db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()
    if existing is not None:
        raise AuthError("Username is already taken.", code="CONFLICT")

    user = User(
        institution_id=institution_id,
        username=username,
        password_hash=hash_password(password),
        subject=username,
    )
    db.add(user)
    db.flush()

    for role in sorted(set(roles)):
        db.add(
            UserRoleAssignment(
                user_id=user.id,
                institution_id=institution_id,
                role=role,
                status="ACTIVE",
            )
        )
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    """Verify a username/password pair.

    The message is deliberately identical for unknown users and bad passwords
    so callers cannot probe which usernames exist.
    """
    failure = AuthError("Incorrect username or password.", code="INVALID_CREDENTIALS")
    if not username or not password:
        raise failure

    user = db.execute(
        select(User).where(User.username == username.strip())
    ).scalar_one_or_none()
    if user is None:
        # Burn comparable time so a missing account is not distinguishable by
        # response latency alone.
        verify_password(password, hash_password("invalid", iterations=10_000))
        raise failure
    if not verify_password(password, user.password_hash):
        raise failure
    return user


def create_session(db: Session, user: User) -> str:
    """Issue a session and return the raw cookie value (only ever stored hashed)."""
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = _utc_now()
    db.add(
        AuthSession(
            token_hash=_token_hash(token),
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(hours=settings.session_ttl_hours),
        )
    )
    db.commit()
    return token


def resolve_session(db: Session, token: Optional[str]) -> Optional[AuthContext]:
    """Turn a raw cookie value into a validated identity, or None."""
    if not token:
        return None
    row = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(AuthSession.token_hash == _token_hash(token))
    ).first()
    if row is None:
        return None
    session_row, user = row
    if session_row.revoked_at is not None:
        return None
    expires = session_row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= _utc_now():
        return None
    return AuthContext(
        user_id=user.id,
        username=user.username,
        institution_id=user.institution_id,
        roles=frozenset(roles_for_user(db, user)),
    )


def revoke_session(db: Session, token: Optional[str]) -> bool:
    """Revoke a session. Safe to call with a missing or unknown token."""
    if not token:
        return False
    session_row = db.execute(
        select(AuthSession).where(AuthSession.token_hash == _token_hash(token))
    ).scalar_one_or_none()
    if session_row is None or session_row.revoked_at is not None:
        return False
    session_row.revoked_at = _utc_now()
    db.commit()
    return True


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
