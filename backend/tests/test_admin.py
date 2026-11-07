import pytest

from app.database import SessionLocal
from app.models import Session, StoredFile, User
from .conftest import make_user
from .test_account import login


@pytest.fixture
def admin(client):
    make_user("boss", "boss-password", is_admin=True)
    return login(client, "boss", "boss-password")


@pytest.fixture
def plain(client):
    make_user("daniel", "correct-horse")
    return login(client, "daniel", "correct-horse")


def upload(client, headers, data=b"CRB1-xx", name="a.txt"):
    return client.post("/file/upload", headers=headers, files={"file": ("b", data)}, data={"filename": name})


# ---------- who is allowed in ----------
@pytest.mark.parametrize("method,path", [("get", "/admin/users"), ("post", "/admin/users"), ("delete", "/admin/users/1")])
def test_admin_routes_need_login(client, method, path):
    kwargs = {"json": {"username": "x", "password": "yyyyyyyy"}} if method == "post" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


@pytest.mark.parametrize("method,path", [("get", "/admin/users"), ("post", "/admin/users"), ("delete", "/admin/users/1")])
def test_regular_users_are_forbidden_from_admin_routes(client, plain, method, path):
    kwargs = {"json": {"username": "newperson", "password": "yyyyyyyy"}} if method == "post" else {}
    r = getattr(client, method)(path, headers=plain, **kwargs)
    assert r.status_code == 403
    assert r.json()["detail"] == "Administrator access required"


def test_forbidden_create_really_did_not_create(client, plain):
    client.post("/admin/users", headers=plain, json={"username": "sneaky", "password": "yyyyyyyy"})
    db = SessionLocal()
    assert db.query(User).filter_by(username="sneaky").count() == 0
    db.close()


# ---------- listing ----------
def test_list_shows_counts_but_never_secrets(client, admin):
    make_user("daniel", "correct-horse")
    d = login(client, "daniel", "correct-horse")
    upload(client, d, b"A" * 100, "one.txt")
    upload(client, d, b"B" * 50, "two.txt")
    rows = {u["username"]: u for u in client.get("/admin/users", headers=admin).json()}
    assert rows["daniel"]["file_count"] == 2 and rows["daniel"]["total_bytes"] == 150
    assert rows["boss"]["file_count"] == 0 and rows["boss"]["total_bytes"] == 0
    assert rows["boss"]["is_admin"] is True and rows["daniel"]["is_admin"] is False
    for row in rows.values():
        assert set(row) == {"id", "username", "is_admin", "file_count", "total_bytes"}


# ---------- creating ----------
def test_admin_can_create_a_user_who_can_then_log_in(client, admin):
    r = client.post("/admin/users", headers=admin, json={"username": "newperson", "password": "welcome-123"})
    assert r.status_code == 201 and r.json()["is_admin"] is False
    assert client.post("/auth/login", json={"username": "newperson", "password": "welcome-123"}).status_code == 200


def test_admin_can_create_another_admin(client, admin):
    r = client.post("/admin/users", headers=admin, json={"username": "boss2", "password": "welcome-123", "is_admin": True})
    assert r.status_code == 201 and r.json()["is_admin"] is True
    second = login(client, "boss2", "welcome-123")
    assert client.get("/admin/users", headers=second).status_code == 200


def test_created_password_is_hashed(client, admin):
    client.post("/admin/users", headers=admin, json={"username": "newperson", "password": "welcome-123"})
    db = SessionLocal()
    stored = db.query(User).filter_by(username="newperson").first().password_hash
    db.close()
    assert "welcome-123" not in stored and stored.startswith("$2")


def test_duplicate_username_is_rejected_case_insensitively(client, admin):
    make_user("daniel", "correct-horse")
    for name in ("daniel", "DANIEL", "Daniel"):
        r = client.post("/admin/users", headers=admin, json={"username": name, "password": "welcome-123"})
        assert r.status_code == 409 and "already exists" in r.json()["detail"]


@pytest.mark.parametrize("bad", ["", "   ", "ab", "has space", "semi;colon", "x" * 33, "emoji😀name"])
def test_bad_usernames_are_rejected(client, admin, bad):
    r = client.post("/admin/users", headers=admin, json={"username": bad, "password": "welcome-123"})
    assert r.status_code == 422


def test_short_password_rejected_when_creating(client, admin):
    r = client.post("/admin/users", headers=admin, json={"username": "newperson", "password": "short"})
    assert r.status_code == 422 and "at least 8" in r.json()["detail"]


# ---------- deleting ----------
def test_delete_removes_user_their_files_and_their_sessions(client, admin, plain):
    upload(client, plain)
    upload(client, plain, b"CRB1-yy", "b.txt")
    users = {u["username"]: u["id"] for u in client.get("/admin/users", headers=admin).json()}
    r = client.delete(f"/admin/users/{users['daniel']}", headers=admin)
    assert r.status_code == 200 and r.json()["files_removed"] == 2 and r.json()["username"] == "daniel"
    db = SessionLocal()
    assert db.query(User).filter_by(username="daniel").count() == 0
    assert db.query(StoredFile).count() == 0
    db.close()
    assert client.get("/files", headers=plain).status_code == 401  # their old token is dead
    assert client.post("/auth/login", json={"username": "daniel", "password": "correct-horse"}).status_code == 401


def test_delete_leaves_other_users_alone(client, admin, plain):
    make_user("guest", "guest-password")
    g = login(client, "guest", "guest-password")
    upload(client, g, b"CRB1-guest", "g.txt")
    daniel_id = {u["username"]: u["id"] for u in client.get("/admin/users", headers=admin).json()}["daniel"]
    client.delete(f"/admin/users/{daniel_id}", headers=admin)
    assert [f["filename"] for f in client.get("/files", headers=g).json()] == ["g.txt"]


def test_admin_cannot_delete_themselves(client, admin):
    my_id = client.get("/admin/users", headers=admin).json()[0]["id"]
    r = client.delete(f"/admin/users/{my_id}", headers=admin)
    assert r.status_code == 400 and "own account" in r.json()["detail"]
    assert client.get("/admin/users", headers=admin).status_code == 200


def test_deleting_a_user_that_does_not_exist_is_404(client, admin):
    assert client.delete("/admin/users/99999", headers=admin).status_code == 404


def test_one_admin_can_delete_another_admin(client, admin):
    client.post("/admin/users", headers=admin, json={"username": "boss2", "password": "welcome-123", "is_admin": True})
    boss2 = {u["username"]: u["id"] for u in client.get("/admin/users", headers=admin).json()}["boss2"]
    assert client.delete(f"/admin/users/{boss2}", headers=admin).status_code == 200
