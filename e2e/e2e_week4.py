"""End-to-end checks for week 4: file search/sort/sizes, storage usage + quota, security headers, same-origin /api.

Dev mode (default): API on :8000 started with CERBERUS_QUOTA_MB=1 and a FRESH database containing
    python -m app.cli create-admin daniel --password correct-horse-9
  and Angular dev server on :4200.
Deployment-style mode:  python e2e_week4.py http://localhost:8080   (e2e/prod_proxy.py serving the built client on :8080
  and forwarding /api to the backend, the same job nginx does in Docker). Only the same-origin checks run in that mode.
"""
import os
import sys
import tempfile
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
APP = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4200"
PROD = APP.endswith(":8080")
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


def make_file(dirpath, name, size):
    path = Path(dirpath) / name
    path.write_bytes(os.urandom(size))
    return str(path)


def upload(page, path, pw="file-pw-123", expect="#upload-ok"):
    """Upload and wait until the list has really refreshed (the success banner appears slightly before the list updates)."""
    name = Path(path).name
    page.set_input_files("#file", path)
    page.fill("#enc-password", pw)
    page.click("#upload")
    try:
        page.wait_for_selector(expect, timeout=15000)
        if expect == "#upload-ok":
            page.wait_for_function(
                "n => [...document.querySelectorAll('#file-list li .meta strong')].some(e => e.innerText.trim() === n)", arg=name, timeout=15000)
    except Exception:
        print("DUMP upload-error:", page.locator("#upload-error").all_inner_texts(), "upload-ok:", page.locator("#upload-ok").all_inner_texts(),
              "list:", names(page), "usage:", page.locator("#usage-label").all_inner_texts())
        raise


def names(page):
    return [t.strip() for t in page.locator("#file-list li .meta strong").all_inner_texts()]


def wait_names(page, expected):
    """Wait for the rendered list to equal `expected` (Angular re-renders a beat after the click/typing), then return it."""
    try:
        page.wait_for_function(
            "e => JSON.stringify([...document.querySelectorAll('#file-list li .meta strong')].map(x => x.innerText.trim())) === JSON.stringify(e)",
            arg=expected, timeout=4000)
    except Exception:
        pass
    return names(page)


tmp = tempfile.mkdtemp()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = browser.new_context(viewport={"width": 1100, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    shot = lambda n: page.screenshot(path=str(SHOTS / n))
    requested = []
    page.on("request", lambda r: requested.append(r.url))

    login(page, "daniel", "correct-horse-9")

    if PROD:
        # ---------------- same-origin /api (what the Docker deployment uses) ----------------
        small = Path(tmp) / "deploy-check.txt"
        small.write_text("served through the /api proxy")
        upload(page, str(small))
        page.wait_for_selector("#file-list")
        check("same-origin: file uploaded through /api and listed", "deploy-check.txt" in names(page))
        page.click("button.open")
        page.fill(".dl-pw", "file-pw-123")
        with page.expect_download() as dl:
            page.click("text=Decrypt & download")
        check("same-origin: downloaded file decrypts to the original", Path(dl.value.path()).read_text() == "served through the /api proxy")
        api_calls = [u for u in requested if "/auth/" in u or "/file" in u or "/me/" in u]
        check("same-origin: every API call went to /api on the page's own origin", api_calls and all(u.startswith(APP + "/api/") for u in api_calls))
        check("same-origin: nothing was sent to port 8000 directly", not any(":8000" in u for u in requested))
        page.wait_for_selector("#file-list")
        shot("42-same-origin-file-list.png")
        page.goto(f"{APP}/account")
        page.wait_for_selector("#change-submit")
        check("same-origin: reloading an Angular route (/account) still loads the app", page.locator("#change-submit").is_visible())
        rows = "".join(f"<div>{u.replace('&', '&amp;')}</div>" for u in requested if "/api/" in u)
        html = ("<body style='margin:0;background:#0d1117;color:#c9d1d9;font:15px/1.7 ui-monospace,Menlo,monospace;padding:26px'>"
                f"<div style='color:#7ee787'>Requests the browser made while page origin was {APP}</div>"
                f"<div style='margin-top:12px'>{rows}</div></body>")
        rp = ctx.new_page()
        rp.set_viewport_size({"width": 900, "height": 140 + 30 * len([u for u in requested if '/api/' in u])})
        rp.set_content(html)
        rp.screenshot(path=str(SHOTS / "43-same-origin-requests.png"))
        rp.close()
    else:
        # ---------------- usage meter on an empty account ----------------
        page.wait_for_selector("#usage")
        check("usage: shows 0 B of 1 MB used on a new account", page.inner_text("#usage-label").strip() == "0 B of 1 MB used")
        check("usage: shows the per-file limit", "Max 25 MB per file" in page.inner_text("#usage"))
        shot("32-usage-meter-empty.png")

        # ---------------- sizes, search, sort ----------------
        upload(page, make_file(tmp, "Quarterly-report.pdf", 90_000))
        upload(page, make_file(tmp, "notes.txt", 2_000))
        upload(page, make_file(tmp, "Budget-2026.xlsx", 20_000))
        page.wait_for_function("document.querySelector('#count') && document.querySelector('#count').innerText.trim() === '3 of 3 files'")
        check("list: count line reads '3 of 3 files'", page.inner_text("#count").strip() == "3 of 3 files")
        first_meta = page.locator("#file-list li .meta span").first.inner_text()
        check("list: each row shows a readable size (KB)", " KB · " in first_meta)
        used = page.inner_text("#usage-label")
        check("usage: label updated after uploads (about 111 KB)", "of 1 MB used" in used and "KB" in used)
        shot("33-file-list-sizes-and-usage.png")

        page.fill("#search", "REPORT")
        check("search: 'REPORT' finds Quarterly-report.pdf ignoring case", wait_names(page, ["Quarterly-report.pdf"]) == ["Quarterly-report.pdf"])
        check("search: count line shows '1 of 3 files'", page.inner_text("#count").strip() == "1 of 3 files")
        shot("34-file-search.png")
        page.fill("#search", "zzz-not-here")
        check("search: no match shows a friendly message", "No files match" in page.inner_text("#no-matches"))
        page.fill("#search", "")
        page.wait_for_function("document.querySelectorAll('#file-list li').length === 3")
        check("search: clearing the box brings every file back", len(names(page)) == 3)

        page.select_option("#sort", "name")
        check("sort: Name A-Z", wait_names(page, ["Budget-2026.xlsx", "notes.txt", "Quarterly-report.pdf"]) == ["Budget-2026.xlsx", "notes.txt", "Quarterly-report.pdf"])
        page.select_option("#sort", "size")
        check("sort: Largest first", wait_names(page, ["Quarterly-report.pdf", "Budget-2026.xlsx", "notes.txt"]) == ["Quarterly-report.pdf", "Budget-2026.xlsx", "notes.txt"])
        shot("35-file-sort-by-size.png")
        page.select_option("#sort", "oldest")
        check("sort: Oldest first", wait_names(page, ["Quarterly-report.pdf", "notes.txt", "Budget-2026.xlsx"])[0] == "Quarterly-report.pdf")

        # ---------------- client-side size check ----------------
        big = make_file(tmp, "too-big.bin", 26 * 1024 * 1024)
        before = len(requested)
        page.set_input_files("#file", big)
        page.fill("#enc-password", "file-pw-123")
        page.click("#upload")
        page.wait_for_function("document.querySelector('#upload-error') && document.querySelector('#upload-error').innerText.includes('limit is')")
        check("size check: over-25 MB file is refused with a clear message", "limit is 25 MB per file" in page.inner_text("#upload-error"))
        check("size check: nothing was sent to the server", not any("/file/upload" in u for u in requested[before:]))
        shot("36-upload-too-large.png")

        # ---------------- server storage quota (1 MB in this run) ----------------
        page.reload()
        page.wait_for_selector("#file-list")
        # delete everything so the quota demo has exact figures
        while page.locator("#file-list li").count():
            page.locator(".delete-btn").first.click()
            page.click("#delete-yes")
            page.wait_for_selector("#delete-ok")
            page.wait_for_function("document.querySelector('#delete-confirm') === null")
        page.wait_for_selector("#empty-state")
        check("quota: account is empty again after deleting the demo files", page.inner_text("#usage-label").startswith("0 B"))

        upload(page, make_file(tmp, "photos-backup.zip", 600_000))
        page.wait_for_function("document.querySelector('#usage-label').innerText.includes('586')")
        check("quota: usage reads 586 KB of 1 MB after a 600,000-byte upload", page.inner_text("#usage-label").strip() == "586 KB of 1 MB used")
        upload(page, make_file(tmp, "contracts.pdf", 350_000))
        page.wait_for_function("document.querySelector('.fill.warn') !== null")
        check("quota: bar turns to the warning color at 90% or more", page.locator(".fill.warn").count() == 1)
        shot("37-storage-nearly-full.png")

        before_files = names(page)
        page.set_input_files("#file", make_file(tmp, "one-more.bin", 200_000))
        page.fill("#enc-password", "file-pw-123")
        page.click("#upload")
        page.wait_for_selector("#upload-error")
        check("quota: upload over the limit is refused with 'Storage limit reached'", "Storage limit reached (1 MB)" in page.inner_text("#upload-error"))
        check("quota: the refused file was not added to the list", names(page) == before_files)
        shot("38-storage-limit-reached.png")

        # delete the 600 KB file, retry the same upload
        row = page.locator("#file-list li", has_text="photos-backup.zip")
        row.locator(".delete-btn").click()
        page.click("#delete-yes")
        page.wait_for_selector("#delete-ok")
        page.wait_for_function("!document.querySelector('#file-list').innerText.includes('photos-backup.zip')")
        upload(page, make_file(tmp, "one-more-retry.bin", 200_000))
        check("quota: after deleting a file the same upload now succeeds", "one-more-retry.bin" in names(page))
        check("list: the old 'Deleted ...' notice is gone once a new upload happens", page.locator("#delete-ok").count() == 0)
        shot("39-storage-freed-and-uploaded.png")

        # ---------------- security headers, as the browser receives them ----------------
        resp = ctx.request.get("http://localhost:8000/health")
        h = resp.headers
        check("headers: nosniff", h.get("x-content-type-options") == "nosniff")
        check("headers: frame denied", h.get("x-frame-options") == "DENY")
        check("headers: no-store", h.get("cache-control") == "no-store")
        check("headers: referrer policy", h.get("referrer-policy") == "no-referrer")
        body = subprocess.run(["curl", "-si", "http://localhost:8000/health"], capture_output=True, text=True, check=True).stdout.replace("\r", "")
        html = ("<body style='margin:0;background:#0d1117;color:#c9d1d9;font:15px/1.6 ui-monospace,Menlo,monospace;padding:26px'>"
                "<div style='color:#7ee787'>$ curl -i http://localhost:8000/health</div><pre style='margin:10px 0 0'>"
                + body.replace("&", "&amp;").replace("<", "&lt;") + "</pre></body>")
        hp = ctx.new_page()
        hp.set_viewport_size({"width": 900, "height": 330})
        hp.set_content(html)
        hp.screenshot(path=str(SHOTS / "40-security-headers.png"))
        hp.close()

    browser.close()

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
