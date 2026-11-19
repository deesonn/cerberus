"""Week 5: see where you're signed in, sign out one device, sign out all the others."""
from datetime import datetime, timedelta, timezone

from app import main
from app.database import SessionLocal
from app.models import Session

from .conftest import make_user


def login(client, user="daniel", pw="correct-horse"):
    return {"Authorization": "Bearer " + client.post("/auth/login", json={"username": user, "password": pw}).json()["token"]}


def sessions(client, headers):
    return client.get("/auth/sessions", headers=headers).json()


# ---- listing ----------------------------------------------------------------

def test_listing_needs_login(client):
    assert client.get("/auth/sessions").status_code == 401


def test_one_login_is_one_current_session(client, auth):
    rows = sessions(client, auth)
    assert len(rows) == 1 and rows[0]["current"] is True


def test_second_login_shows_up_and_only_one_is_current(client, auth):
    other = login(client)
    rows = sessions(client, auth)
    assert len(rows) == 2
    assert [r["current"] for r in rows].count(True) == 1
    mine_from_other = [r for r in sessions(client, other) if r["current"]][0]["id"]
    mine_here = [r for r in rows if r["current"]][0]["id"]
    assert mine_from_other != mine_here


def test_listing_never_contains_a_token(client, auth):
    raw = client.get("/auth/sessions", headers=auth).text
    assert auth["Authorization"].split(" ")[1] not in raw
    assert set(sessions(client, auth)[0]) == {"id", "created_at", "expires_at", "current"}


def test_newest_login_is_listed_first(client, auth):
    login(client)
    rows = sessions(client, auth)
    assert rows[0]["created_at"] >= rows[1]["created_at"]


def test_expiry_is_the_start_plus_session_lifetime(client, auth):
    row = sessions(client, auth)[0]
    start = datetime.fromisoformat(row["created_at"]).replace(tzinfo=None)
    end = datetime.fromisoformat(row["expires_at"]).replace(tzinfo=None)
    assert end - start == main.SESSION_LIFETIME


def test_expired_sessions_are_not_listed(client, auth):
    db = SessionLocal()
    old = Session(token="old-token", user_id=1, created_at=datetime.now(timezone.utc) - timedelta(days=2))
    db.add(old); db.commit(); db.close()
    assert len(sessions(client, auth)) == 1


def test_users_only_see_their_own_sessions(client, auth):
    make_user("guest", "guest-pass-1")
    guest = login(client, "guest", "guest-pass-1")
    assert len(sessions(client, guest)) == 1
    assert len(sessions(client, auth)) == 1


# ---- revoking one -----------------------------------------------------------

def test_revoking_another_device_signs_it_out(client, auth):
    other = login(client)
    target = [r for r in sessions(client, auth) if not r["current"]][0]["id"]
    assert client.delete(f"/auth/sessions/{target}", headers=auth).status_code == 200
    assert client.get("/files", headers=other).status_code == 401
    assert client.get("/files", headers=auth).status_code == 200


def test_cannot_revoke_the_current_session_this_way(client, auth):
    mine = sessions(client, auth)[0]["id"]
    r = client.delete(f"/auth/sessions/{mine}", headers=auth)
    assert r.status_code == 400
    assert client.get("/files", headers=auth).status_code == 200


def test_unknown_session_id_is_404(client, auth):
    assert client.delete("/auth/sessions/does-not-exist", headers=auth).status_code == 404


def test_cannot_revoke_someone_elses_session(client, auth):
    make_user("guest", "guest-pass-1")
    guest = login(client, "guest", "guest-pass-1")
    guest_id = sessions(client, guest)[0]["id"]
    assert client.delete(f"/auth/sessions/{guest_id}", headers=auth).status_code == 404
    assert client.get("/files", headers=guest).status_code == 200


def test_revoking_needs_login(client):
    assert client.delete("/auth/sessions/abc").status_code == 401


# ---- sign out everywhere else -----------------------------------------------

def test_logout_others_keeps_only_this_device(client, auth):
    a, b = login(client), login(client)
    r = client.post("/auth/logout-others", headers=auth)
    assert r.json()["signed_out"] == 2
    assert client.get("/files", headers=a).status_code == 401
    assert client.get("/files", headers=b).status_code == 401
    assert client.get("/files", headers=auth).status_code == 200


def test_logout_others_with_nothing_else_signed_in(client, auth):
    assert client.post("/auth/logout-others", headers=auth).json()["signed_out"] == 0


def test_logout_others_leaves_other_users_alone(client, auth):
    make_user("guest", "guest-pass-1")
    guest = login(client, "guest", "guest-pass-1")
    client.post("/auth/logout-others", headers=auth)
    assert client.get("/files", headers=guest).status_code == 200


def test_logout_others_needs_login(client):
    assert client.post("/auth/logout-others").status_code == 401
