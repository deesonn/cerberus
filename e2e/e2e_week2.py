"""End-to-end checks for session expiry and file deletion; saves screenshots to docs/screenshots/.

Prereqs: API on :8000, Angular dev server on :4200, user 'daniel' / 'correct-horse-9' (created with the CLI).
"""
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
DB = ROOT / "backend" / "cerberus.db"
API = "http://localhost:8000"
APP = "http://localhost:4200"
results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def age_all_sessions(hours):
    con = sqlite3.connect(DB)
    ts = (datetime.now(timezone.utc) - timedelta(hours=hours)).replace(tzinfo=None).isoformat(sep=" ")
    con.execute("update sessions set created_at = ?", (ts,))
    con.commit()
    con.close()


def login(page):
    page.goto(f"{APP}/login")
    page.fill("#username", "daniel")
    page.fill("#password", "correct-horse-9")
    page.click("#submit")
    page.wait_for_selector("#upload")


def upload(page, name, text):
    f = Path(tempfile.mkdtemp()) / name
    f.write_text(text)
    page.set_input_files("#file", str(f))
    page.fill("#enc-password", "file-pw-123")
    page.click("#upload")
    page.wait_for_selector("#upload-ok")
    page.wait_for_function(f"document.querySelector('#file-list')?.innerText.includes('{name}')")


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = browser.new_context(viewport={"width": 1100, "height": 780})
    page = ctx.new_page()
    shot = lambda n: page.screenshot(path=str(SHOTS / n))

    # start from a clean slate for repeatability
    login(page)
    token = page.evaluate("sessionStorage.getItem('cerberus.token')")
    hdr = {"Authorization": f"Bearer {token}"}
    for f in ctx.request.get(f"{API}/files", headers=hdr).json():
        ctx.request.delete(f"{API}/file/{f['hash']}", headers=hdr)
    page.reload()
    page.wait_for_selector("#empty-state")

    # ---------- file deletion ----------
    upload(page, "quarterly-report.txt", "Q3 numbers: confidential")
    upload(page, "vacation-notes.txt", "Flights and hotel details")
    items = page.locator("#file-list li")
    check("delete-setup: two files listed", items.count() == 2)

    first = items.nth(0)
    victim_name = first.locator("strong").inner_text()
    victim_hash = [f for f in ctx.request.get(f"{API}/files", headers=hdr).json() if f["filename"] == victim_name][0]["hash"]

    first.locator("button.delete-btn").click()
    page.wait_for_selector("#delete-confirm")
    check("delete-confirm-prompt: asks before deleting and names the file", victim_name in page.inner_text("#delete-confirm"))
    shot("12-delete-confirmation.png")

    page.click("#delete-no")
    page.wait_for_selector("#delete-confirm", state="detached")
    check("delete-cancel: 'Keep file' leaves both files in place", page.locator("#file-list li").count() == 2 and not page.locator("#delete-confirm").is_visible())

    page.locator("#file-list li").nth(0).locator("button.delete-btn").click()
    page.wait_for_selector("#delete-confirm")
    page.click("#delete-yes")
    page.wait_for_selector("#delete-ok")
    check("delete-success: success notice shown", victim_name in page.inner_text("#delete-ok"))
    check("delete-success: only one file left in the list", page.locator("#file-list li").count() == 1 and victim_name not in page.inner_text("#file-list"))
    shot("13-file-deleted.png")

    gone = ctx.request.get(f"{API}/file/{victim_hash}", headers=hdr)
    check("delete-server-side: deleted file is really gone (404 from the API)", gone.status == 404)
    con = sqlite3.connect(DB)
    check("delete-server-side: ciphertext row removed from database",
          con.execute("select count(*) from files where hash = ?", (victim_hash,)).fetchone()[0] == 0)
    con.close()

    # ---------- session expiry ----------
    age_all_sessions(9)  # pretend the session is 9 hours old (limit is 8)
    page.reload()
    page.wait_for_selector("#session-notice")
    check("session-expired: redirected to /login?reason=expired", "/login" in page.url and "reason=expired" in page.url)
    check("session-expired: clear 'session expired' message shown", "expired" in page.inner_text("#session-notice").lower())
    check("session-expired: local token cleared", page.evaluate("sessionStorage.getItem('cerberus.token')") is None)
    shot("14-session-expired.png")

    # logging back in works and the remaining file is still there
    page.fill("#username", "daniel")
    page.fill("#password", "correct-horse-9")
    page.click("#submit")
    page.wait_for_selector("#file-list")
    check("session-expired: signing in again works and shows the surviving file", page.locator("#file-list li").count() == 1)

    # unknown/invalid token (e.g. server forgot it) -> polite redirect, not a broken screen
    page.evaluate("sessionStorage.setItem('cerberus.token', 'not-a-real-token')")
    page.reload()
    page.wait_for_selector("#session-notice")
    check("invalid-token: redirected with 'please sign in' notice", "reason=signin" in page.url and "sign in" in page.inner_text("#session-notice").lower())

    browser.close()

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
