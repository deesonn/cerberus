"""Week 4: security headers, configurable CORS, per-user storage quota."""
import io

from app import main

from .conftest import make_user


def _up(client, auth, data: bytes, name="a.bin"):
    return client.post("/file/upload", headers=auth, files={"file": ("blob", io.BytesIO(data))}, data={"filename": name})


# ---- security headers -------------------------------------------------------

def test_headers_on_normal_response(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"


def test_headers_on_error_response(client):
    r = client.get("/files")  # 401
    assert r.status_code == 401
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"


def test_headers_on_file_download(client, auth):
    digest = _up(client, auth, b"cipher-bytes").json()["hash"]
    r = client.get(f"/file/{digest}", headers=auth)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-frame-options"] == "DENY"


# ---- CORS -------------------------------------------------------------------

def test_cors_allows_the_configured_origin(client):
    r = client.options("/auth/login", headers={"Origin": "http://localhost:4200", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:4200"


def test_cors_refuses_other_origins(client):
    r = client.options("/auth/login", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers


# ---- storage usage ----------------------------------------------------------

def test_storage_requires_login(client):
    assert client.get("/me/storage").status_code == 401


def test_storage_starts_empty(client, auth):
    body = client.get("/me/storage", headers=auth).json()
    assert body["used_bytes"] == 0 and body["file_count"] == 0
    assert body["quota_bytes"] == main.QUOTA_BYTES
    assert body["max_upload_bytes"] == main.MAX_UPLOAD_BYTES


def test_storage_counts_uploads_and_drops_after_delete(client, auth):
    a = _up(client, auth, b"x" * 100, "a").json()
    _up(client, auth, b"y" * 50, "b")
    body = client.get("/me/storage", headers=auth).json()
    assert (body["used_bytes"], body["file_count"]) == (150, 2)
    client.delete(f"/file/{a['hash']}", headers=auth)
    body = client.get("/me/storage", headers=auth).json()
    assert (body["used_bytes"], body["file_count"]) == (50, 1)


def test_storage_is_per_user(client, auth):
    _up(client, auth, b"x" * 100)
    make_user("guest", "guest-pass-1")
    tok = client.post("/auth/login", json={"username": "guest", "password": "guest-pass-1"}).json()["token"]
    body = client.get("/me/storage", headers={"Authorization": f"Bearer {tok}"}).json()
    assert (body["used_bytes"], body["file_count"]) == (0, 0)


# ---- quota ------------------------------------------------------------------

def test_upload_over_quota_is_refused(client, auth, monkeypatch):
    monkeypatch.setattr(main, "QUOTA_BYTES", 100)
    assert _up(client, auth, b"a" * 60, "one").status_code == 200
    r = _up(client, auth, b"b" * 60, "two")  # 120 > 100
    assert r.status_code == 413
    assert "Storage limit reached" in r.json()["detail"]


def test_refused_upload_stores_nothing(client, auth, monkeypatch):
    monkeypatch.setattr(main, "QUOTA_BYTES", 100)
    _up(client, auth, b"a" * 60, "one")
    _up(client, auth, b"b" * 60, "two")
    assert [f["filename"] for f in client.get("/files", headers=auth).json()] == ["one"]


def test_exactly_filling_the_quota_is_allowed(client, auth, monkeypatch):
    monkeypatch.setattr(main, "QUOTA_BYTES", 100)
    assert _up(client, auth, b"a" * 100).status_code == 200


def test_deleting_frees_room(client, auth, monkeypatch):
    monkeypatch.setattr(main, "QUOTA_BYTES", 100)
    first = _up(client, auth, b"a" * 80, "one").json()
    assert _up(client, auth, b"b" * 80, "two").status_code == 413
    client.delete(f"/file/{first['hash']}", headers=auth)
    assert _up(client, auth, b"b" * 80, "two").status_code == 200


def test_one_users_files_dont_use_up_anothers_quota(client, auth, monkeypatch):
    monkeypatch.setattr(main, "QUOTA_BYTES", 100)
    _up(client, auth, b"a" * 100, "big")
    make_user("guest", "guest-pass-1")
    tok = client.post("/auth/login", json={"username": "guest", "password": "guest-pass-1"}).json()["token"]
    r = client.post("/file/upload", headers={"Authorization": f"Bearer {tok}"},
                    files={"file": ("blob", io.BytesIO(b"c" * 100))}, data={"filename": "mine"})
    assert r.status_code == 200


def test_duplicate_is_reported_before_quota(client, auth, monkeypatch):
    monkeypatch.setattr(main, "QUOTA_BYTES", 100)
    _up(client, auth, b"a" * 100)
    assert _up(client, auth, b"a" * 100).status_code == 409
