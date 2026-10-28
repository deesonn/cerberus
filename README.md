# Cerberus

*A three-headed guardian for your files.* Files are encrypted in your browser with a password only you know, before they ever reach the server. The server stores ciphertext it cannot read.

- `backend/` - FastAPI + SQLite (SQLAlchemy). Login/logout with 8-hour session expiry, upload/list/download/delete of encrypted files, bcrypt-hashed passwords, admin CLI.
- `client/` - Angular app. Login (with a clear "session expired" redirect), upload with client-side AES-GCM encryption (Web Crypto, PBKDF2 key derivation), file list, decrypt & download, delete with confirmation.
- `e2e/` - Browser end-to-end tests (`e2e_smoke.py`: login/upload/decrypt/logout; `e2e_week2.py`: delete + session expiry) that drive the real app and save the screenshots in `docs/screenshots/`.
- `docs/DESIGN.md` - how it works and the decisions behind it.

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
(cd backend && python -m pytest)               # 31 backend tests
(cd client && CHROME_BIN=/path/to/chrome npx ng test --watch=false --browsers=ChromeHeadlessNoSandbox)   # 12 crypto unit tests
pip install playwright
python e2e/e2e_smoke.py && python e2e/e2e_week2.py   # need both servers running + user daniel / correct-horse-9
```

Accounts are created by an administrator through the CLI on purpose; there is no public sign-up page in the MVP.
