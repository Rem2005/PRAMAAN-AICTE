"""Local credentials and server-side sessions.

Adds the columns needed for local authentication and a session table that
stores only the SHA-256 of the cookie value, so session revocation works and a
database read alone cannot be replayed as a login.

The `users` table is populated only by the CLI in this prototype, so the new
NOT NULL columns carry an empty server default to keep the migration safe on a
database that already contains user rows; rows with an empty password hash
cannot authenticate.

Revision ID: 0005_auth_sessions
Revises: 0004_batch_academic_year
Create Date: 2026-10-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0005_auth_sessions"
down_revision = "0004_batch_academic_year"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "username",
            sa.String(length=255),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(length=512),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.create_index("uq_users_username", "users", ["username"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_session_user"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_auth_sessions_token_hash", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("uq_users_username", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
