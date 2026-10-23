import os

from app.database import SessionLocal
from app.models import StoredFile
from .conftest import make_user


def upload(client, auth, data=b"\x01ciphertext-bytes", name="notes.txt"):
    return client.post("/file/upload", headers=auth, files={"file": ("blob", data)}, data={"filename": name})


def test_new_user_has_empty_file_list(client, auth):
    r = client.get("/files", headers=auth)
    assert r.status_code == 200 and r.json() == []


def test_upload_then_list_then_download_roundtrip(client, auth):
    blob = os.urandom(2048)
    r = upload(client, auth, blob)
    assert r.status_code == 200
    file_hash = r.json()["hash"]

    listing = client.get("/files", headers=auth).json()
    assert [f["filename"] for f in listing] == ["notes.txt"]
    assert listing[0]["hash"] == file_hash

    dl = client.get(f"/file/{file_hash}", headers=auth)
    assert dl.status_code == 200
    assert dl.content == blob  # server hands back exactly the stored bytes, nothing more


def test_server_stores_exactly_what_the_client_sent(client, auth):
    blob = b"pretend-this-is-aes-gcm-output"
    upload(client, auth, blob)
    db = SessionLocal()
    stored = db.query(StoredFile).first().ciphertext
    db.close()
    assert stored == blob


def test_upload_requires_login(client):
    r = client.post("/file/upload", files={"file": ("blob", b"x")}, data={"filename": "a"})
    assert r.status_code == 401


def test_empty_upload_rejected(client, auth):
    assert upload(client, auth, b"").status_code == 400


def test_oversized_upload_rejected_with_clear_error(client, auth):
    r = upload(client, auth, b"x" * (25 * 1024 * 1024 + 1))
    assert r.status_code == 413
    assert "too large" in r.json()["detail"].lower()


def test_user_cannot_fetch_or_list_another_users_file(client, auth):
    file_hash = upload(client, auth).json()["hash"]
    make_user("mallory", "mallory-password")
    tok = client.post("/auth/login", json={"username": "mallory", "password": "mallory-password"}).json()["token"]
    other = {"Authorization": f"Bearer {tok}"}
    assert client.get(f"/file/{file_hash}", headers=other).status_code == 404
    assert client.get("/files", headers=other).json() == []
