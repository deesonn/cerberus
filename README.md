# Cerberus

*A three-headed guardian for your files.* Files are encrypted in your browser with a password only you know, before they ever reach the server. The server stores ciphertext it cannot read.

- `backend/` - FastAPI + SQLite (SQLAlchemy). Login/logout, upload/list/download of encrypted files, bcrypt-hashed passwords, admin CLI.
- `client/` - Angular app. Login, upload with client-side AES-GCM encryption (Web Crypto, PBKDF2 key derivation), file list, decrypt & download.
- `e2e/` - Browser end-to-end test that drives the real app and saves the screenshots in `docs/screenshots/`.
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
(cd backend && python -m pytest)               # 21 backend tests
pip install playwright && python e2e/e2e_smoke.py   # needs both servers running + user daniel / correct-horse-9
```

Accounts are created by an administrator through the CLI on purpose; there is no public sign-up page in the MVP.
