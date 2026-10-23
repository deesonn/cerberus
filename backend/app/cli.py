"""Admin CLI. Account creation lives here on purpose, not in the web app."""
import argparse
import getpass
import sys

from sqlalchemy.exc import OperationalError

from . import models
from .database import Base, SessionLocal, engine
from .security import hash_password


def _create(username: str, password: str | None, is_admin: bool) -> int:
    username = username.strip()
    if not username:
        print("Error: username can't be blank.", file=sys.stderr)
        return 1
    if password is None:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Confirm password: "):
            print("Error: passwords didn't match.", file=sys.stderr)
            return 1
    if len(password) < 8:
        print("Error: password must be at least 8 characters.", file=sys.stderr)
        return 1
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            if db.query(models.User).filter(models.User.username == username).first():
                print(f"Error: username '{username}' already exists. Nothing was changed.", file=sys.stderr)
                return 1
            db.add(models.User(username=username, password_hash=hash_password(password), is_admin=is_admin))
            db.commit()
        finally:
            db.close()
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
