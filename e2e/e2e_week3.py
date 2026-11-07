"""End-to-end checks for change-password and admin user management; saves screenshots to docs/screenshots/.

Prereqs: API on :8000 and Angular dev server on :4200, started against a FRESH database with:
    python -m app.cli create-admin daniel --password correct-horse-9
    python -m app.cli create-user guest --password guest-pass-1
(This test changes guest's password and deletes guest at the end, so re-create the database to run it again.)
"""
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
APP = "http://localhost:4200"
results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def login(page, user, pw):
    page.goto(f"{APP}/login")
    page.fill("#username", user)
    page.fill("#password", pw)
    page.click("#submit")


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx_a = browser.new_context(viewport={"width": 1100, "height": 780})   # guest, "laptop"
    ctx_b = browser.new_context(viewport={"width": 1100, "height": 780})   # guest, "phone"
    ctx_admin = browser.new_context(viewport={"width": 1100, "height": 860})
    a, b, adm = ctx_a.new_page(), ctx_b.new_page(), ctx_admin.new_page()
    shot = lambda page, n: page.screenshot(path=str(SHOTS / n))

    # ---------------- regular user cannot see or reach the admin area ----------------
    login(a, "guest", "guest-pass-1")
    a.wait_for_selector("#upload")
    check("non-admin: header has Files and Account links", a.locator("#nav-account").is_visible() and a.locator("#nav-files").is_visible())
    check("non-admin: no Admin link in the header", a.locator("#nav-admin").count() == 0)
    a.goto(f"{APP}/admin")
    a.wait_for_selector("#upload")
    check("non-admin: typing /admin in the address bar bounces back to the file list", not a.url.rstrip("/").endswith("/admin"))
    shot(a, "19-nonadmin-header.png")

    # upload a file as guest so we can show the admin deleting an account with files
    f = Path(tempfile.mkdtemp()) / "guest-notes.txt"
    f.write_text("guest private notes")
    a.set_input_files("#file", str(f))
    a.fill("#enc-password", "file-pw-123")
    a.click("#upload")
    a.wait_for_selector("#upload-ok")

    # second "device" signed in as the same guest
    login(b, "guest", "guest-pass-1")
    b.wait_for_selector("#upload")

    # ---------------- change password ----------------
    a.click("#nav-account")
    a.wait_for_selector("#change-submit")
    a.fill("#current-password", "guest-pass-1")
    a.fill("#new-password", "new-guest-pass-2")
    a.fill("#confirm-password", "something-else-entirely")
    a.click("#change-submit")
    a.wait_for_selector("#account-error")
    check("change-password: mismatched confirmation is caught before sending", "don't match" in a.inner_text("#account-error"))

    a.fill("#confirm-password", "new-guest-pass-2")
    a.fill("#new-password", "short")
    a.fill("#confirm-password", "short")
    a.click("#change-submit")
    a.wait_for_function("document.querySelector('#account-error')?.innerText.includes('at least 8')")
    check("change-password: too-short new password is caught", "at least 8" in a.inner_text("#account-error"))

    a.fill("#current-password", "WRONG-current")
    a.fill("#new-password", "new-guest-pass-2")
    a.fill("#confirm-password", "new-guest-pass-2")
    a.click("#change-submit")
    a.wait_for_function("document.querySelector('#account-error')?.innerText.includes('incorrect')")
    check("change-password: wrong current password refused with a clear message", "incorrect" in a.inner_text("#account-error"))
    shot(a, "20-change-password-wrong-current.png")

    a.fill("#current-password", "guest-pass-1")
    a.click("#change-submit")
    a.wait_for_selector("#account-ok")
    check("change-password: success message says the other device was signed out", "1 other signed-in device was signed out" in a.inner_text("#account-ok"))
    check("change-password: form fields are cleared after success", a.input_value("#current-password") == "" and a.input_value("#new-password") == "")
    shot(a, "21-change-password-success.png")

    # the other device is kicked out the next time it talks to the server
    b.reload()
    b.wait_for_selector("#session-notice")
    check("change-password: the other device lands on /login with a notice", "/login" in b.url and "reason=signin" in b.url)
    shot(b, "22-other-device-signed-out.png")
    check("change-password: the device that changed it stays signed in", a.locator("#nav-account").is_visible())

    # old password no longer works, new one does
    a.click("#logout")
    a.wait_for_url("**/login")
    login(a, "guest", "guest-pass-1")
    a.wait_for_selector("#form-error")
    check("change-password: old password is rejected on the login page", "incorrect" in a.inner_text("#form-error").lower())
    a.fill("#password", "new-guest-pass-2")
    a.click("#submit")
    a.wait_for_selector("#file-list")
    check("change-password: new password logs in and the encrypted file is still listed", "guest-notes.txt" in a.inner_text("#file-list"))

    # ---------------- admin area ----------------
    login(adm, "daniel", "correct-horse-9")
    adm.wait_for_selector("#nav-admin")
    check("admin: Admin link appears in the header", adm.locator("#nav-admin").is_visible())
    adm.click("#nav-admin")
    adm.wait_for_selector("#user-table")
    guest_row = adm.locator('tr[data-user="guest"]')
    check("admin: list shows guest with 1 file", "1" in guest_row.locator("td.num").nth(0).inner_text())
    check("admin: list shows the admin's own row marked 'you' with no Delete button",
          adm.locator('tr[data-user="daniel"] .you').count() == 1 and adm.locator('tr[data-user="daniel"] button').count() == 0)
    check("admin: never shows any password hash or file name", "$2" not in adm.inner_text("#user-table") and "guest-notes" not in adm.inner_text("main"))

    adm.fill("#new-username", "guest")
    adm.fill("#new-user-password", "whatever-123")
    adm.click("#create-user")
    adm.wait_for_selector("#admin-error")
    check("admin: duplicate username refused", "already exists" in adm.inner_text("#admin-error"))
    adm.fill("#new-username", "GUEST")
    adm.click("#create-user")
    adm.wait_for_function("document.querySelector('#admin-error')?.innerText.includes('already exists')")
    check("admin: duplicate check ignores capitalization", "already exists" in adm.inner_text("#admin-error"))
    adm.fill("#new-username", "new hire")
    adm.click("#create-user")
    adm.wait_for_function("document.querySelector('#admin-error')?.innerText.includes('Username must be')")
    check("admin: username with a space refused", "Username must be" in adm.inner_text("#admin-error"))
    adm.fill("#new-username", "newhire")
    adm.fill("#new-user-password", "short")
    adm.click("#create-user")
    adm.wait_for_function("document.querySelector('#admin-error')?.innerText.includes('at least 8')")
    check("admin: short starting password refused", "at least 8" in adm.inner_text("#admin-error"))

    adm.fill("#new-user-password", "welcome-123")
    adm.click("#create-user")
    adm.wait_for_selector("#admin-ok")
    adm.wait_for_selector('tr[data-user="newhire"]')
    check("admin: new account created and appears in the list", 'Created user "newhire"' in adm.inner_text("#admin-ok"))
    shot(adm, "23-admin-users-page.png")

    # the new account can sign in
    c = browser.new_context().new_page()
    login(c, "newhire", "welcome-123")
    c.wait_for_selector("#upload")
    check("admin: the new user can sign in with the starting password", c.locator("#nav-account").is_visible())

    # delete flow: cancel, then confirm (guest has 1 file and a live session in context a)
    adm.locator('tr[data-user="guest"] button.del').click()
    adm.wait_for_selector("#del-yes")
    check("admin: delete asks first and says how many files go with the account", "1 file" in adm.inner_text('tr[data-user="guest"]'))
    shot(adm, "24-admin-delete-confirm.png")
    adm.click("#del-no")
    adm.wait_for_selector("#del-yes", state="detached")
    check("admin: Cancel keeps the account", adm.locator('tr[data-user="guest"]').count() == 1)

    adm.locator('tr[data-user="guest"] button.del').click()
    adm.wait_for_selector("#del-yes")
    adm.click("#del-yes")
    adm.wait_for_function("document.querySelector('#admin-ok')?.innerText.includes('Deleted')")
    adm.wait_for_selector('tr[data-user="guest"]', state="detached")
    check("admin: delete reports the account and file count removed", 'Deleted "guest" and 1 file.' in adm.inner_text("#admin-ok"))
    shot(adm, "25-admin-account-deleted.png")

    a.reload()
    a.wait_for_selector("#session-notice")
    check("admin: the deleted user's open session is dead (sent to /login)", "/login" in a.url)
    login(a, "guest", "new-guest-pass-2")
    a.wait_for_selector("#form-error")
    check("admin: the deleted user can't sign in any more", "incorrect" in a.inner_text("#form-error").lower())

    browser.close()

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
