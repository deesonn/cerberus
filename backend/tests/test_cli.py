from app import cli
from app.database import SessionLocal
from app.models import User


def test_create_admin_succeeds_and_sets_admin_flag(capsys):
    assert cli.main(["create-admin", "boss", "--password", "supersecret1"]) == 0
    db = SessionLocal()
    user = db.query(User).filter_by(username="boss").first()
    db.close()
    assert user.is_admin is True
    assert user.password_hash != "supersecret1"


def test_duplicate_username_rejected_and_nothing_changed(capsys):
    cli.main(["create-admin", "boss", "--password", "supersecret1"])
    assert cli.main(["create-admin", "boss", "--password", "different-pw-2"]) == 1
    assert "already exists" in capsys.readouterr().err
    db = SessionLocal()
    original_hash = db.query(User).filter_by(username="boss").first().password_hash
    db.close()
    from app.security import verify_password
    assert verify_password("supersecret1", original_hash)


def test_short_password_rejected(capsys):
    assert cli.main(["create-admin", "boss", "--password", "short"]) == 1


def test_unreachable_database_gives_clear_error(capsys, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    bad = create_engine("sqlite:////nonexistent-dir/nope.db")
    monkeypatch.setattr(cli, "engine", bad)
    monkeypatch.setattr(cli, "SessionLocal", sessionmaker(bind=bad))
    assert cli.main(["create-admin", "boss", "--password", "supersecret1"]) == 2
    assert "couldn't reach the database" in capsys.readouterr().err
