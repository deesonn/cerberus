"""Account rules in one place, so the admin CLI and the admin web routes can't drift apart."""
import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models
from .security import hash_password

MIN_PASSWORD_LENGTH = 8
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")


class AccountError(Exception):
    """A rule was broken. `status` is the HTTP code the web routes answer with."""

    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.message = message
        self.status = status


def clean_username(raw: str) -> str:
    username = (raw or "").strip()
    if not username:
        raise AccountError("Username can't be blank.")
    if not USERNAME_RE.match(username):
        raise AccountError("Username must be 3-32 characters: letters, numbers, dots, dashes or underscores.")
    return username


def check_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise AccountError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


def username_taken(db: Session, username: str) -> bool:
    # Case-insensitive so "Daniel" can't be created next to "daniel" and confuse everyone.
    return db.query(models.User).filter(func.lower(models.User.username) == username.lower()).first() is not None


def create_account(db: Session, username: str, password: str, is_admin: bool = False) -> models.User:
    username = clean_username(username)
    check_password(password)
    if username_taken(db, username):
        raise AccountError(f"Username '{username}' already exists. Nothing was changed.", status=409)
    user = models.User(username=username, password_hash=hash_password(password), is_admin=is_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
