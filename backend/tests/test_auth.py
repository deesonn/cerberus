from app.database import SessionLocal
from app.models import User
from .conftest import make_user


def test_health_checks_db(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_login_success(client):
    make_user()
    r = client.post("/auth/login", json={"username": "daniel", "password": "correct-horse"})
    assert r.status_code == 200
    assert r.json()["token"]


def test_login_missing_username(client):
    make_user()
    r = client.post("/auth/login", json={"username": "", "password": "correct-horse"})
    assert r.status_code == 422


def test_login_missing_password(client):
    make_user()
    r = client.post("/auth/login", json={"username": "daniel", "password": ""})
    assert r.status_code == 422


def test_login_wrong_password_and_unknown_user_look_identical(client):
    make_user()
    bad_pw = client.post("/auth/login", json={"username": "daniel", "password": "nope"})
    bad_user = client.post("/auth/login", json={"username": "ghost", "password": "nope"})
    assert bad_pw.status_code == bad_user.status_code == 401
    assert bad_pw.json() == bad_user.json()


def test_login_rate_limited_after_repeated_failures(client):
    make_user()
    for _ in range(5):
        client.post("/auth/login", json={"username": "daniel", "password": "nope"})
    # even the right password is refused during the lockout
    r = client.post("/auth/login", json={"username": "daniel", "password": "correct-horse"})
    assert r.status_code == 429


def test_protected_route_requires_login(client):
    assert client.get("/files").status_code == 401


def test_logout_really_kills_the_session(client, auth):
    assert client.get("/files", headers=auth).status_code == 200
    assert client.post("/auth/logout", headers=auth).status_code == 200
    assert client.get("/files", headers=auth).status_code == 401


def test_logout_twice_is_fine(client, auth):
    client.post("/auth/logout", headers=auth)
    assert client.post("/auth/logout", headers=auth).status_code == 200


def test_password_is_stored_hashed_not_plaintext():
    make_user(password="correct-horse")
    db = SessionLocal()
    stored = db.query(User).first().password_hash
    db.close()
    assert "correct-horse" not in stored
    assert stored.startswith("$2")  # bcrypt identifier
