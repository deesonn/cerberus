import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["CERBERUS_DB_URL"] = f"sqlite:///{_tmp}/test.db"

import pytest
from fastapi.testclient import TestClient

from app import main
from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    main._failed_logins.clear()
    yield


@pytest.fixture
def client():
    return TestClient(main.app)


def make_user(username="daniel", password="correct-horse", is_admin=False):
    db = SessionLocal()
    db.add(User(username=username, password_hash=hash_password(password), is_admin=is_admin))
    db.commit()
    db.close()


@pytest.fixture
def auth(client):
    make_user()
    token = client.post("/auth/login", json={"username": "daniel", "password": "correct-horse"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}
