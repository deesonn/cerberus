import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import models
from .database import Base, engine, get_db
from .security import verify_password

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 60
SESSION_LIFETIME = timedelta(hours=float(os.environ.get("CERBERUS_SESSION_HOURS", "8")))

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cerberus")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# username -> (failed_count, window_start). In-memory is fine for a single-instance MVP.
_failed_logins: dict[str, tuple[int, float]] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


def current_user(authorization: str | None = Header(default=None), db: DbSession = Depends(get_db)) -> models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    session = db.get(models.Session, token)
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # SQLite hands back naive datetimes; they were stored as UTC.
    age = datetime.now(timezone.utc).replace(tzinfo=None) - session.created_at.replace(tzinfo=None)
    if age > SESSION_LIFETIME:
        # Remove the dead session so it can never be revived, and tell the client why.
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")
    return db.get(models.User, session.user_id)


@app.get("/health")
def health(db: DbSession = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/auth/login")
def login(body: LoginRequest, db: DbSession = Depends(get_db)):
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=422, detail="Username and password are both required")

    count, started = _failed_logins.get(username, (0, 0.0))
    if count >= MAX_FAILED_LOGINS and time.time() - started < LOCKOUT_SECONDS:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in a minute.")
    if count >= MAX_FAILED_LOGINS:
        count = 0

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        _failed_logins[username] = (count + 1, started if count else time.time())
        # Same message either way so the response doesn't reveal which usernames exist.
        raise HTTPException(status_code=401, detail="Username or password is incorrect")

    _failed_logins.pop(username, None)
    token = secrets.token_urlsafe(32)
    db.add(models.Session(token=token, user_id=user.id))
    db.commit()
    return {"token": token, "username": user.username, "is_admin": user.is_admin}


@app.post("/auth/logout")
def logout(authorization: str | None = Header(default=None), db: DbSession = Depends(get_db)):
    # Idempotent: logging out an already-dead session is still a success.
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        session = db.get(models.Session, token)
        if session is not None:
            db.delete(session)
            db.commit()
    return {"status": "logged out"}


@app.get("/files")
def list_files(user: models.User = Depends(current_user), db: DbSession = Depends(get_db)):
    rows = (
        db.query(models.StoredFile)
        .filter(models.StoredFile.owner_id == user.id)
        .order_by(models.StoredFile.uploaded_at.desc())
        .all()
    )
    return [
        {"hash": r.hash, "filename": r.filename, "size": r.size, "uploaded_at": r.uploaded_at.isoformat()}
        for r in rows
    ]


@app.post("/file/upload")
async def upload_file(
    file: UploadFile = File(...),
    filename: str = Form(...),
    user: models.User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large (25 MB max)")
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    digest = hashlib.sha256(data).hexdigest()
    if db.query(models.StoredFile).filter(models.StoredFile.hash == digest).first():
        raise HTTPException(status_code=409, detail="This file has already been uploaded")
    # `data` is the ciphertext the client produced. The server never sees plaintext or a key.
    db.add(models.StoredFile(owner_id=user.id, filename=filename, hash=digest, size=len(data), ciphertext=data))
    db.commit()
    return {"hash": digest, "filename": filename, "size": len(data)}


@app.get("/file/{file_hash}")
def get_file(file_hash: str, user: models.User = Depends(current_user), db: DbSession = Depends(get_db)):
    row = (
        db.query(models.StoredFile)
        .filter(models.StoredFile.hash == file_hash, models.StoredFile.owner_id == user.id)
        .first()
    )
    if row is None:
        # 404 (not 403) so a user can't probe for other people's file hashes.
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=row.ciphertext, media_type="application/octet-stream")


@app.delete("/file/{file_hash}")
def delete_file(file_hash: str, user: models.User = Depends(current_user), db: DbSession = Depends(get_db)):
    row = (
        db.query(models.StoredFile)
        .filter(models.StoredFile.hash == file_hash, models.StoredFile.owner_id == user.id)
        .first()
    )
    if row is None:
        # Same 404 whether the file doesn't exist or belongs to someone else.
        raise HTTPException(status_code=404, detail="File not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "hash": file_hash}
