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


def _age_session(token: str, hours: float):
    """Pretend the session was created `hours` ago by rewriting its timestamp."""
    from datetime import datetime, timedelta, timezone
    from app.models import Session
    db = SessionLocal()
    s = db.get(Session, token)
    s.created_at = (datetime.now(timezone.utc) - timedelta(hours=hours)).replace(tzinfo=None)
    db.commit()
    db.close()


def test_session_still_valid_just_inside_the_lifetime(client, auth):
    _age_session(auth["Authorization"].split()[1], 7.9)
    assert client.get("/files", headers=auth).status_code == 200


def test_expired_session_is_rejected_with_a_clear_reason(client, auth):
    _age_session(auth["Authorization"].split()[1], 8.1)
    r = client.get("/files", headers=auth)
    assert r.status_code == 401
    assert r.json()["detail"] == "Session expired"


def test_expired_session_is_deleted_and_stays_dead(client, auth):
    from app.models import Session
    token = auth["Authorization"].split()[1]
    _age_session(token, 9)
    client.get("/files", headers=auth)
    db = SessionLocal()
    assert db.get(Session, token) is None
    db.close()
    # second try now looks like any unknown token
    assert client.get("/files", headers=auth).json()["detail"] == "Not authenticated"


def test_logging_in_again_after_expiry_works(client, auth):
    _age_session(auth["Authorization"].split()[1], 9)
    r = client.post("/auth/login", json={"username": "daniel", "password": "correct-horse"})
    assert r.status_code == 200
    fresh = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.get("/files", headers=fresh).status_code == 200
