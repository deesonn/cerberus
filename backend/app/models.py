from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, String
from .database import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)  # bcrypt hash, never plaintext
    is_admin = Column(Boolean, default=False, nullable=False)


class Session(Base):
    __tablename__ = "sessions"
    token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)


class StoredFile(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    hash = Column(String, unique=True, nullable=False, index=True)  # sha256 of the ciphertext
    size = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=_now, nullable=False)
    ciphertext = Column(LargeBinary, nullable=False)  # only ever the encrypted blob
