"""Admin CLI. Account creation lives here on purpose, not in the web app."""
import argparse
import getpass
import sys

from sqlalchemy.exc import OperationalError

from .accounts import AccountError, create_account
from .database import Base, SessionLocal, engine


def _create(username: str, password: str | None, is_admin: bool) -> int:
    if password is None:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Confirm password: "):
            print("Error: passwords didn't match.", file=sys.stderr)
            return 1
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            user = create_account(db, username, password, is_admin=is_admin)
            username = user.username
        finally:
            db.close()
    except AccountError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        return 1
    except OperationalError as exc:
        print(f"Error: couldn't reach the database ({exc.orig}). Check CERBERUS_DB_URL and permissions.", file=sys.stderr)
        return 2
    role = "administrator" if is_admin else "user"
    print(f"Created {role} '{username}'.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cerberus-admin")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("create-admin", "create-user"):
        p = sub.add_parser(name)
        p.add_argument("username")
        p.add_argument("--password", help="Skip the prompt (handy for scripts/tests)")
    args = parser.parse_args(argv)
    return _create(args.username, args.password, is_admin=(args.command == "create-admin"))


if __name__ == "__main__":
    sys.exit(main())
