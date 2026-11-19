"""End-to-end checks for week 5: signed-in devices (list, sign one out, sign all others out) and renaming files.

Needs a FRESH database with an admin and a regular user, the API on :8000 and the Angular dev server on :4200:
    python -m app.cli create-admin daniel --password correct-horse-9
    python -m app.cli create-user guest --password guest-pass-1
Each "device" is its own browser context, so it has its own sessionStorage and its own login, like a real second browser.
"""
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
APP = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4200"
results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def login(page, user, pw):
    page.goto(f"{APP}/login")
    page.fill("#username", user)
    page.fill("#password", pw)
    page.click("#submit")
    page.wait_for_selector("#upload")


def open_account(page, rows):
    page.goto(f"{APP}/account")
    page.wait_for_function(f"document.querySelectorAll('#session-list li').length === {rows}", timeout=8000)


def rows_text(page):
    return [t.strip() for t in page.locator("#session-list li").all_inner_texts()]


def names(page):
    return [t.strip() for t in page.locator("#file-list li .meta strong").all_inner_texts()]


tmp = tempfile.mkdtemp()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    def new_device(width=1100, height=900):
        ctx = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
        return ctx, ctx.new_page()

    ctx_a, A = new_device()
    shot = lambda page, n: page.screenshot(path=str(SHOTS / n))

    # ---------------- sessions ----------------
    login(A, "daniel", "correct-horse-9")
    open_account(A, 1)
    check("sessions: one login shows one row", len(rows_text(A)) == 1)
    check("sessions: that row is marked 'This device'", "This device" in rows_text(A)[0] and A.locator("#this-device").count() == 1)
    check("sessions: row says when it started and how long is left", "Signed in just now" in rows_text(A)[0] and "h" in rows_text(A)[0] and "left" in rows_text(A)[0])
    check("sessions: 'Sign out all other devices' is disabled with nothing else signed in", A.locator("#logout-others").is_disabled())
    check("sessions: no Sign out button on this device's own row", A.locator("#session-list li button").count() == 0)
    A.locator("#sessions-card").screenshot(path=str(SHOTS / "47-sessions-one-device.png"))

    ctx_b, B = new_device(420, 860)
    login(B, "daniel", "correct-horse-9")
    open_account(A, 2)
    texts = rows_text(A)
    check("sessions: second login makes two rows", len(texts) == 2)
    check("sessions: exactly one row is 'This device' and one is 'Another device'",
          sum("This device" in t for t in texts) == 1 and sum("Another device" in t for t in texts) == 1)
    check("sessions: button now offers to sign out 1 other device", "(1)" in A.inner_text("#logout-others") and A.locator("#logout-others").is_enabled())
    A.locator("#sessions-card").screenshot(path=str(SHOTS / "48-sessions-two-devices.png"))

    A.locator("#session-list li", has_text="Another device").locator("button.revoke").click()
    A.wait_for_selector("#sessions-ok")
    A.wait_for_function("document.querySelectorAll('#session-list li').length === 1")
    check("sessions: signing out the other device removes its row and says so", "That device was signed out" in A.inner_text("#sessions-ok"))
    B.goto(f"{APP}/")
    B.wait_for_url("**/login*", timeout=8000)
    check("sessions: the signed-out device is sent to the login page", "/login" in B.url)
    check("sessions: this device is still signed in", A.locator("#session-list li").count() == 1)

    login(B, "daniel", "correct-horse-9")
    ctx_c, C = new_device(420, 860)
    login(C, "daniel", "correct-horse-9")
    open_account(A, 3)
    check("sessions: three devices show three rows", len(rows_text(A)) == 3)
    check("sessions: button says (2)", "(2)" in A.inner_text("#logout-others"))
    A.click("#logout-others")
    A.wait_for_selector("#sessions-ok")
    A.wait_for_function("document.querySelectorAll('#session-list li').length === 1")
    check("sessions: 'Sign out all other devices' reports 2 and leaves one row", "2 other devices were signed out" in A.inner_text("#sessions-ok"))
    A.locator("#sessions-card").screenshot(path=str(SHOTS / "49-sessions-signed-out-others.png"))
    for name, page in (("B", B), ("C", C)):
        page.goto(f"{APP}/")
        page.wait_for_url("**/login*", timeout=8000)
        check(f"sessions: device {name} was signed out", "/login" in page.url)
    check("sessions: this device can still open its file list", A.goto(f"{APP}/") and A.wait_for_selector("#upload") is not None)

    ctx_g, G = new_device()
    login(G, "guest", "guest-pass-1")
    open_account(G, 1)
    check("sessions: a different user sees only their own single session", len(rows_text(G)) == 1)
    ctx_g.close(); ctx_b.close(); ctx_c.close()

    # ---------------- rename ----------------
    A.goto(f"{APP}/")
    A.wait_for_selector("#upload")
    src = Path(tmp) / "draft-notes.txt"
    src.write_text("hello from before the rename")
    A.set_input_files("#file", str(src))
    A.fill("#enc-password", "file-pw-123")
    A.click("#upload")
    A.wait_for_function("[...document.querySelectorAll('#file-list li .meta strong')].some(e => e.innerText.trim() === 'draft-notes.txt')")

    patches = []
    A.on("request", lambda r: patches.append((r.method, r.url, r.post_data)) if r.method == "PATCH" else None)

    A.locator("#file-list li", has_text="draft-notes.txt").locator("button.rename-btn").click()
    A.wait_for_selector("#rename-input")
    check("rename: the box starts with the current name", A.input_value("#rename-input") == "draft-notes.txt")

    A.fill("#rename-input", "   ")
    A.click("#rename-save")
    A.wait_for_selector("#rename-error")
    check("rename: an empty name is refused in the browser with a clear message", "can't be empty" in A.inner_text("#rename-error"))
    A.fill("#rename-input", "../secrets.txt")
    A.click("#rename-save")
    A.wait_for_function("document.querySelector('#rename-error').innerText.includes('slashes')")
    check("rename: a name with slashes is refused", "slashes" in A.inner_text("#rename-error"))
    check("rename: neither refused name was sent to the server", len(patches) == 0)
    shot(A, "50-rename-rejected.png")

    A.fill("#rename-input", "draft-notes.txt")
    A.click("#rename-save")
    A.wait_for_function("document.querySelector('#rename-input') === null")
    check("rename: saving the unchanged name just closes the editor without a request", len(patches) == 0)

    A.locator("#file-list li", has_text="draft-notes.txt").locator("button.rename-btn").click()
    A.fill("#rename-input", "meeting-notes-final.txt")
    A.click("#rename-cancel")
    A.wait_for_function("document.querySelector('#rename-input') === null")
    check("rename: Cancel keeps the old name", names(A) == ["draft-notes.txt"] and len(patches) == 0)

    A.locator("#file-list li", has_text="draft-notes.txt").locator("button.rename-btn").click()
    A.fill("#rename-input", "  meeting-notes-final.txt ")
    A.screenshot(path=str(SHOTS / "51-rename-editing.png"))
    A.click("#rename-save")
    A.wait_for_selector("#rename-ok")
    A.wait_for_function("[...document.querySelectorAll('#file-list li .meta strong')].some(e => e.innerText.trim() === 'meeting-notes-final.txt')")
    check("rename: the list shows the new name", names(A) == ["meeting-notes-final.txt"])
    check("rename: a message says what changed", 'Renamed "draft-notes.txt" to "meeting-notes-final.txt"' in A.inner_text("#rename-ok"))
    check("rename: exactly one PATCH was sent, with the trimmed name", len(patches) == 1 and '"meeting-notes-final.txt"' in (patches[0][2] or ""))
    shot(A, "52-rename-done.png")

    A.locator("#file-list li", has_text="meeting-notes-final.txt").locator("button.open").click()
    A.fill(".dl-pw", "file-pw-123")
    with A.expect_download() as dl:
        A.click("text=Decrypt & download")
    check("rename: the download is saved under the new name", dl.value.suggested_filename == "meeting-notes-final.txt")
    check("rename: and still decrypts to the original text (renaming didn't touch the encrypted bytes)",
          Path(dl.value.path()).read_text() == "hello from before the rename")
    A.reload()
    A.wait_for_selector("#file-list")
    check("rename: the new name survives a page reload", names(A) == ["meeting-notes-final.txt"])

    ctx_a.close()
    browser.close()

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
