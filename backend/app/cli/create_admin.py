"""Create the first administrator.

Usage (from the backend directory):

    python -m app.cli.create_admin --email admin@example.com --full-name "System Admin"

The password is requested interactively so it is less likely to be stored in shell history.
The command refuses to run after an administrator already exists.
"""

import argparse
import getpass
import sys

from app.common.exceptions import AppError
from app.core.database import SessionLocal
from app.users.service import create_initial_admin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create the initial administrator account.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument(
        "--password",
        help="Prefer omitting this flag so the password is read from a hidden prompt.",
    )
    parser.add_argument(
        "--preferred-language",
        default="en",
        choices=["en", "mr", "hi"],
    )
    args = parser.parse_args(argv)
    password = args.password or getpass.getpass("Password: ")
    if args.password is None:
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            return 1
    db = SessionLocal()
    try:
        create_initial_admin(
            db,
            email=args.email,
            full_name=args.full_name,
            password=password,
            preferred_language=args.preferred_language,
        )
    except AppError as exc:
        print(exc.message, file=sys.stderr)
        return 1
    finally:
        db.close()
    print("Administrator account created. Sign in with the admin access screen after this.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
