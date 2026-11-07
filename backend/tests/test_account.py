from app.database import SessionLocal
from app.models import Session, User
from app.security import verify_password
from .conftest import make_user


def login(client, username="daniel", password="correct-horse"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def change(client, headers, current="correct-horse", new="a-brand-new-pass"):
    return client.post("/auth/change-password", headers=headers, json={"current_password": current, "new_password": new})


def test_change_password_success_then_new_password_works_and_old_does_not(client, auth):
    r = change(client, auth)
    assert r.status_code == 200 and r.json()["status"] == "password changed"
    assert client.post("/auth/login", json={"username": "daniel", "password": "correct-horse"}).status_code == 401
    assert client.post("/auth/login", json={"username": "daniel", "password": "a-brand-new-pass"}).status_code == 200


def test_new_password_is_stored_hashed(client, auth):
    change(client, auth, new="a-brand-new-pass")
    db = SessionLocal()
    stored = db.query(User).filter_by(username="daniel").first().password_hash
    db.close()
    assert "a-brand-new-pass" not in stored and stored.startswith("$2")
    assert verify_password("a-brand-new-pass", stored)


def test_wrong_current_password_is_refused_and_nothing_changes(client, auth):
    r = change(client, auth, current="not-my-password")
    assert r.status_code == 403
    assert r.json()["detail"] == "Current password is incorrect"
    assert client.post("/auth/login", json={"username": "daniel", "password": "correct-horse"}).status_code == 200


def test_too_short_new_password_rejected(client, auth):
    r = change(client, auth, new="short")
    assert r.status_code == 422 and "at least 8" in r.json()["detail"]


def test_new_password_must_differ_from_current(client, auth):
    r = change(client, auth, new="correct-horse")
    assert r.status_code == 422 and "different" in r.json()["detail"]


def test_change_password_requires_login(client):
    r = client.post("/auth/change-password", json={"current_password": "x", "new_password": "yyyyyyyyy"})
    assert r.status_code == 401


def test_other_sessions_are_signed_out_but_this_one_stays(client, auth):
    other = login(client)  # a second device logged in as the same user
    assert client.get("/files", headers=other).status_code == 200
    r = change(client, auth)
    assert r.json()["other_sessions_signed_out"] == 1
    assert client.get("/files", headers=other).status_code == 401  # the old device is kicked out
    assert client.get("/files", headers=auth).status_code == 200  # the device that changed it is not


def test_other_users_sessions_are_untouched(client, auth):
    make_user("guest", "guest-password")
    guest = login(client, "guest", "guest-password")
    change(client, auth)
    assert client.get("/files", headers=guest).status_code == 200


def test_repeated_wrong_current_passwords_trigger_the_lockout(client, auth):
    for _ in range(5):
        change(client, auth, current="nope-nope")
    # even the correct current password is refused during the lockout
    assert change(client, auth).status_code == 429


def test_encrypted_files_still_open_after_account_password_change(client, auth):
    """File passwords are separate from the account password, so changing it must not touch stored files."""
    blob = b"CRB1-pretend-ciphertext"
    h = client.post("/file/upload", headers=auth, files={"file": ("b", blob)}, data={"filename": "a.txt"}).json()["hash"]
    change(client, auth)
    fresh = login(client, password="a-brand-new-pass")
    assert client.get(f"/file/{h}", headers=fresh).content == blob


def test_lockout_still_works_for_normal_logins_after_refactor(client):
    make_user()
    for _ in range(5):
        client.post("/auth/login", json={"username": "daniel", "password": "bad"})
    assert client.post("/auth/login", json={"username": "daniel", "password": "correct-horse"}).status_code == 429
