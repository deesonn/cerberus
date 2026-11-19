"""Week 5: renaming a file, plus the filename rules that upload and rename now share."""
import io

from .conftest import make_user


def upload(client, auth, name="a.bin", data=b"cipher-bytes"):
    return client.post("/file/upload", headers=auth, files={"file": ("blob", io.BytesIO(data))}, data={"filename": name})


def rename(client, auth, digest, name):
    return client.patch(f"/file/{digest}", headers=auth, json={"filename": name})


def test_rename_changes_the_listed_name(client, auth):
    digest = upload(client, auth, "old.txt").json()["hash"]
    r = rename(client, auth, digest, "new name.txt")
    assert r.status_code == 200 and r.json() == {"hash": digest, "filename": "new name.txt"}
    assert client.get("/files", headers=auth).json()[0]["filename"] == "new name.txt"


def test_rename_trims_spaces(client, auth):
    digest = upload(client, auth).json()["hash"]
    assert rename(client, auth, digest, "   tidy.txt  ").json()["filename"] == "tidy.txt"


def test_rename_does_not_touch_the_encrypted_bytes(client, auth):
    digest = upload(client, auth, data=b"secret-ciphertext").json()["hash"]
    rename(client, auth, digest, "other.txt")
    assert client.get(f"/file/{digest}", headers=auth).content == b"secret-ciphertext"
    assert client.get("/files", headers=auth).json()[0]["hash"] == digest


def test_rename_keeps_size_and_upload_time(client, auth):
    digest = upload(client, auth).json()["hash"]
    before = client.get("/files", headers=auth).json()[0]
    rename(client, auth, digest, "x.txt")
    after = client.get("/files", headers=auth).json()[0]
    assert (after["size"], after["uploaded_at"]) == (before["size"], before["uploaded_at"])


def test_empty_name_is_refused_and_nothing_changes(client, auth):
    digest = upload(client, auth, "keep.txt").json()["hash"]
    assert rename(client, auth, digest, "   ").status_code == 422
    assert client.get("/files", headers=auth).json()[0]["filename"] == "keep.txt"


def test_slashes_are_refused(client, auth):
    digest = upload(client, auth).json()["hash"]
    assert rename(client, auth, digest, "../etc/passwd").status_code == 422
    assert rename(client, auth, digest, "a\\b").status_code == 422


def test_control_characters_are_refused(client, auth):
    digest = upload(client, auth).json()["hash"]
    assert rename(client, auth, digest, "bad\nname").status_code == 422


def test_too_long_is_refused_but_255_is_fine(client, auth):
    digest = upload(client, auth).json()["hash"]
    assert rename(client, auth, digest, "a" * 256).status_code == 422
    assert rename(client, auth, digest, "a" * 255).status_code == 200


def test_two_files_may_share_a_name(client, auth):
    a = upload(client, auth, "one", b"11").json()["hash"]
    b = upload(client, auth, "two", b"22").json()["hash"]
    assert rename(client, auth, a, "same.txt").status_code == 200
    assert rename(client, auth, b, "same.txt").status_code == 200


def test_rename_needs_login(client, auth):
    digest = upload(client, auth).json()["hash"]
    assert client.patch(f"/file/{digest}", json={"filename": "x"}).status_code == 401


def test_cannot_rename_someone_elses_file(client, auth):
    digest = upload(client, auth, "mine.txt").json()["hash"]
    make_user("guest", "guest-pass-1")
    tok = client.post("/auth/login", json={"username": "guest", "password": "guest-pass-1"}).json()["token"]
    r = client.patch(f"/file/{digest}", headers={"Authorization": f"Bearer {tok}"}, json={"filename": "stolen.txt"})
    assert r.status_code == 404
    assert client.get("/files", headers=auth).json()[0]["filename"] == "mine.txt"


def test_rename_unknown_file_is_404(client, auth):
    assert rename(client, auth, "0" * 64, "x.txt").status_code == 404


def test_missing_filename_field_is_422(client, auth):
    digest = upload(client, auth).json()["hash"]
    assert client.patch(f"/file/{digest}", headers=auth, json={}).status_code == 422


def test_upload_uses_the_same_filename_rules(client, auth):
    assert upload(client, auth, "   ").status_code == 422
    assert upload(client, auth, "a/b.txt").status_code == 422
    assert upload(client, auth, "  spaced.txt ").json()["filename"] == "spaced.txt"
