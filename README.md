# Cerberus

*A three-headed guardian for your files.* Files are encrypted in your browser with a password only you know, before they ever reach the server. The server stores ciphertext it cannot read.

- `backend/` - FastAPI + SQLite (SQLAlchemy). Login/logout with 8-hour session expiry, change-password, upload/list/download/delete of encrypted files, per-account storage quota, security headers, signed-in device list with sign-out, file rename, bcrypt-hashed passwords, admin routes (list/create/delete accounts) and admin CLI. Full route list: `docs/API.md`.
- `client/` - Angular app. Login (with a clear "session expired" redirect), upload with client-side AES-GCM encryption (Web Crypto, PBKDF2 key derivation), file list, decrypt & download, delete with confirmation, an Account page (change password) and an Admin page (create/delete accounts, admins only).
- `e2e/` - Browser end-to-end tests (`e2e_smoke.py`: login/upload/decrypt/logout; `e2e_week2.py`: delete + session expiry; `e2e_week3.py`: change password + admin accounts) that drive the real app and save the screenshots in `docs/screenshots/`.
- `docs/DESIGN.md` - how it works and the decisions behind it. `docs/API.md` - every route. `docs/DEPLOY.md` - running it with Docker (`docker compose up --build`). `docs/USE_CASES.md` - the use-case narratives (13 so far).
- `.github/workflows/ci.yml` - runs the backend tests and the client build + unit tests on every push.

## Run it

```bash
# 1. backend
cd backend
pip install -r requirements.txt
python -m app.cli create-admin daniel          # prompts for a password (min 8 chars)
python -m app.cli create-user guest            # regular, non-admin account
python -m uvicorn app.main:app --port 8000

# 2. client (new terminal)
cd client
npm install
npx ng serve --port 4200                       # open http://localhost:4200

# 3. tests
(cd backend && python -m pytest)               # 115 backend tests
(cd client && CHROME_BIN=/path/to/chrome npx ng test --watch=false --browsers=ChromeHeadlessNoSandbox)   # 48 client unit tests (crypto, file list helpers, API base, session times, filename rules)
pip install playwright
python e2e/e2e_smoke.py && python e2e/e2e_week2.py   # need both servers running + user daniel / correct-horse-9
python e2e/e2e_week5.py   # fresh DB with daniel (admin) + guest; signed-in devices and renaming
python e2e/e2e_week4.py   # fresh DB with daniel (admin) and the API started with CERBERUS_QUOTA_MB=1; add http://localhost:8080 to test the same-origin /api setup via e2e/prod_proxy.py
python e2e/e2e_week3.py   # needs a FRESH database with daniel (admin) and guest / guest-pass-1; it changes guest's password and deletes guest
```

Accounts are created by an administrator (CLI or the Admin page) on purpose; there is no public sign-up page in the MVP.
