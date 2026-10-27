"""Provision local accounts.

Usage:

    NEW_USER_PASSWORD='...' python -m app.cli create-user \\
        --username operator1 --institution 1 --role INSTITUTION_DATA_OPERATOR

The password is read from the NEW_USER_PASSWORD environment variable so it is
never passed on the command line (where it would land in shell history and
process listings) and never committed to the repository. The command refuses
to run when the variable is unset or empty.
"""

import argparse
import os
import sys

from app.db.models import Institution
from app.db.session import get_session_local
from app.services.auth import (
    ROLE_ADMIN,
    ROLE_AUDITOR,
    ROLE_NODAL,
    ROLE_OPERATOR,
    AuthError,
    create_user,
)

KNOWN_ROLES = (
    ROLE_OPERATOR,
    ROLE_NODAL,
    ROLE_AUDITOR,
    ROLE_ADMIN,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-user", help="Create a local account")
    create.add_argument("--username", required=True)
    create.add_argument("--institution", required=True, type=int)
    create.add_argument(
        "--role",
        required=True,
        action="append",
        choices=KNOWN_ROLES,
        help="Repeat for multiple roles",
    )

    inst = sub.add_parser("create-institution", help="Register an institution")
    inst.add_argument("--code", required=True)
    inst.add_argument("--name", required=True)

    seed = sub.add_parser(
        "seed-demo",
        help=(
            "Seed SYNTHETIC demo data: an institution (optional), demo accounts "
            "(needs DEMO_PASSWORD) and an approved snapshot plus active policy"
        ),
    )
    seed.add_argument("--institution", type=int, help="Existing institution id")
    seed.add_argument("--code", help="Institution code to create if missing")
    seed.add_argument("--name", help="Institution name when creating it")
    seed.add_argument(
        "--academic-year", default="2026-2027", help="Academic year for the snapshot"
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "create-user":
        password = os.environ.get("NEW_USER_PASSWORD", "")
        if not password:
            print(
                "Refusing to create a user: NEW_USER_PASSWORD is not set.\n"
                "Provide it through the environment, never in the repository.",
                file=sys.stderr,
            )
            return 2

        session_factory = get_session_local()
        db = session_factory()
        try:
            user = create_user(
                db,
                username=args.username,
                password=password,
                institution_id=args.institution,
                roles=args.role,
            )
        except AuthError as exc:
            print(f"Could not create user: {exc.message}", file=sys.stderr)
            return 1
        except Exception:
            # Deliberately terse: a driver traceback would expose schema and
            # connection details that do not belong on a terminal or in a log.
            print(
                "Could not create user. Is the database reachable and migrated "
                "(python -m alembic upgrade head)?",
                file=sys.stderr,
            )
            return 1
        finally:
            db.close()

        print(
            f"Created user '{user.username}' (id {user.id}) for institution "
            f"{user.institution_id} with roles: {', '.join(args.role)}"
        )
        return 0

    if args.command == "seed-demo":
        return _seed_demo(args)

    if args.command == "create-institution":
        session_factory = get_session_local()
        db = session_factory()
        try:
            existing = db.query(Institution).filter(
                Institution.official_code == args.code
            ).first()
            if existing is not None:
                print(
                    f"Institution code '{args.code}' already exists "
                    f"(id {existing.id}).",
                    file=sys.stderr,
                )
                return 1
            institution = Institution(
                official_code=args.code, name=args.name, status="ACTIVE"
            )
            db.add(institution)
            db.commit()
            db.refresh(institution)
        except Exception:
            print(
                "Could not create institution. Is the database reachable and "
                "migrated (python -m alembic upgrade head)?",
                file=sys.stderr,
            )
            return 1
        finally:
            db.close()

        print(
            f"Created institution '{institution.name}' (id {institution.id}, "
            f"code {institution.official_code})."
        )
        return 0

    return 2


DEMO_ACCOUNTS = (
    ("operator1", [ROLE_OPERATOR]),
    ("nodal1", [ROLE_NODAL]),
    ("auditor1", [ROLE_AUDITOR]),
)


def _seed_demo(args) -> int:
    """Create synthetic demo data. Everything it writes is labelled SYNTHETIC."""
    from app.fixtures.demo import seed_demo

    session_factory = get_session_local()
    db = session_factory()
    try:
        if args.institution is not None:
            institution = db.get(Institution, args.institution)
            if institution is None:
                print(
                    f"Institution {args.institution} not found. Pass --code to "
                    "create one instead.",
                    file=sys.stderr,
                )
                return 1
        elif args.code and args.name:
            institution = db.query(Institution).filter(
                Institution.official_code == args.code
            ).first()
            if institution is None:
                institution = Institution(
                    official_code=args.code, name=args.name, status="ACTIVE"
                )
                db.add(institution)
                db.commit()
                db.refresh(institution)
                print(
                    f"Created institution '{institution.name}' "
                    f"(id {institution.id}, code {institution.official_code})."
                )
            else:
                print(
                    f"Using existing institution '{institution.name}' "
                    f"(id {institution.id})."
                )
        else:
            print(
                "Pass either --institution <id>, or --code and --name to create one.",
                file=sys.stderr,
            )
            return 2

        password = os.environ.get("DEMO_PASSWORD", "")
        if password:
            for username, roles in DEMO_ACCOUNTS:
                try:
                    create_user(
                        db,
                        username=username,
                        password=password,
                        institution_id=institution.id,
                        roles=roles,
                    )
                except AuthError as exc:
                    if exc.code != "CONFLICT":
                        print(
                            f"Could not create '{username}': {exc.message}",
                            file=sys.stderr,
                        )
                        return 1
                    print(f"Account '{username}' already exists; left unchanged.")
                else:
                    print(
                        f"Created account '{username}' with roles: "
                        f"{', '.join(roles)}"
                    )
        else:
            print(
                "DEMO_PASSWORD is not set, so no demo accounts were created.\n"
                "Set it (DEMO_PASSWORD='...' python -m app.cli seed-demo ...) to "
                "create operator1, nodal1 and auditor1."
            )

        summary = seed_demo(
            db,
            institution_id=institution.id,
            academic_year=args.academic_year,
        )
    except Exception:
        print(
            "Could not seed demo data. Is the database reachable and migrated "
            "(python -m alembic upgrade head)?",
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()

    print(
        "\nSynthetic demo data ready "
        f"(institution {summary['institution_id']}, "
        f"academic year {summary['academic_year']})."
    )
    print(
        f"Approved snapshot #{summary['snapshot_id']} v{summary['snapshot_version']}, "
        f"active policy #{summary['policy_id']} v{summary['policy_version']}."
    )
    if summary["created"]:
        print("Created: " + ", ".join(summary["created"]))
    if summary["existing"]:
        print("Already present: " + ", ".join(summary["existing"]))
    print("These figures are SYNTHETIC and are not an official intake record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
