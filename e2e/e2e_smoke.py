"""End-to-end smoke test for Cerberus. Drives the real Angular app + FastAPI server in a browser,
checks the outcomes from the Test Plans sheet, and saves screenshots to docs/screenshots/.

Prereqs: API on :8000, Angular dev server on :4200, users 'daniel' / 'correct-horse-9' created via the CLI.
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
DB = ROOT / "backend" / "cerberus.db"
SHOTS.mkdir(parents=True, exist_ok=True)

SECRET_TEXT = "Cerberus test document. Account number 000-111-222. Do not share."
results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium") if Path("/opt/pw-browsers/chromium").exists() else p.chromium.launch()
    page = browser.new_page(viewport={"width": 1100, "height": 780}, accept_downloads=True)
    shot = lambda n: page.screenshot(path=str(SHOTS / n))

    # login-redirect: not logged in -> bounced to /login
    page.goto("http://localhost:4200/")
    page.wait_for_url("**/login")
    check("login-redirect: unauthenticated visit to home lands on /login", page.url.endswith("/login"))

    # login-page-load
    expect(page.locator("#username")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()
    expect(page.locator("#submit")).to_be_visible()
    check("login-page-load: username, password, submit visible", True)
    shot("01-login-page.png")

    # login-missing-username / password
    page.fill("#password", "whatever")
    page.click("#submit")
    page.wait_for_selector("#username-error")
    check("login-missing-username: red error under username", page.locator("#username-error").is_visible())
    page.fill("#username", "daniel")
    page.fill("#password", "")
    page.click("#submit")
    page.wait_for_selector("#password-error")
    check("login-missing-password: red error under password", page.locator("#password-error").is_visible())
    shot("02-login-required-fields.png")

    # login-bad-credentials
    page.fill("#username", "daniel")
    page.fill("#password", "wrong-password")
    page.click("#submit")
    page.wait_for_selector("#form-error")
    check("login-bad-credentials: generic incorrect message, still on /login",
          "incorrect" in page.inner_text("#form-error").lower() and page.url.endswith("/login"))
    shot("03-login-bad-credentials.png")

    # login-success -> empty state
    page.fill("#password", "correct-horse-9")
    page.click("#submit")
    page.wait_for_selector("#empty-state")
    check("login-success + list-empty-state: lands on file list with empty message", page.locator("#empty-state").is_visible())
    shot("04-file-list-empty.png")

    # upload-missing-password
    plain = Path(tempfile.mkdtemp()) / "secret-notes.txt"
    plain.write_text(SECRET_TEXT)
    page.set_input_files("#file", str(plain))
    page.click("#upload")
    page.wait_for_selector("#upload-error")
    check("upload-missing-password: blocked client-side with message", "encryption password" in page.inner_text("#upload-error").lower())

    # upload-success
    page.fill("#enc-password", "my-file-password")
    page.click("#upload")
    page.wait_for_selector("#file-list")
    check("upload-success: file appears in list", "secret-notes.txt" in page.inner_text("#file-list"))
    shot("05-upload-and-file-list.png")

    # upload-stored-encrypted / security-file-ciphertext (check raw bytes in the DB)
    con = sqlite3.connect(DB)
    (blob,) = con.execute("select ciphertext from files limit 1").fetchone()
    con.close()
    check("upload-stored-encrypted: plaintext not present in stored bytes", b"Cerberus" not in blob and b"000-111-222" not in blob)
    check("upload-stored-encrypted: stored blob starts with CRB1 header", blob[:4] == b"CRB1")

    # decrypt-wrong-password
    page.click("button.open")
    page.fill(".dl-pw", "not-the-password")
    page.click("text=Decrypt & download")
    page.wait_for_selector(".dl-error")
    check("decrypt-wrong-password: clear 'incorrect password' message", "incorrect password" in page.inner_text(".dl-error").lower())
    shot("06-decrypt-wrong-password.png")

    # decrypt-correct-password
    page.fill(".dl-pw", "my-file-password")
    with page.expect_download() as dl:
        page.click("text=Decrypt & download")
    out = Path(dl.value.path()).read_text()
    check("decrypt-correct-password: downloaded file matches original", out == SECRET_TEXT)
    check("decrypt-correct-password: original filename preserved", dl.value.suggested_filename == "secret-notes.txt")

    # logout-ends-session
    page.click("#logout")
    page.wait_for_url("**/login")
    page.goto("http://localhost:4200/")
    page.wait_for_url("**/login")
    check("logout-ends-session: back on /login and home redirects to /login", page.url.endswith("/login"))
    shot("07-after-logout.png")
    browser.close()

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
