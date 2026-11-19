# Cerberus - design notes

## The one rule
The server must never be able to read a file. Everything else follows from that.

## Upload (client-side encryption)
1. User picks a file and types an encryption password (separate from their login password).
2. Browser derives a 256-bit key from the password with PBKDF2-SHA256 (310,000 iterations, random 16-byte salt).
3. Browser encrypts the file with AES-GCM (random 12-byte IV).
4. Browser uploads `CRB1 | salt | iv | ciphertext+tag`. The server stores those bytes as-is and indexes them by their SHA-256.

The server never receives the password, the key, or the plaintext. AES-GCM authenticates the data, so a wrong password fails loudly rather than returning garbage.

## Download and delete
`GET /file/{hash}` returns the stored bytes, only to the owning account (other users get 404, so hashes can't be probed). The browser decrypts locally and saves the file under its original name.

`DELETE /file/{hash}` permanently removes the stored ciphertext, again owner-only with the same 404 for anyone else. The UI asks "Delete permanently?" first because there is no undo and no recovery.

## Auth
- Passwords are stored as bcrypt hashes. Login returns a random session token; logout deletes it server-side so a copied token stops working.
- Sessions last 8 hours (`CERBERUS_SESSION_HOURS` to change). An expired session is deleted on first use and the API answers `401 Session expired`; the Angular client catches any 401 on a protected call, clears its token, and sends the user to `/login` with a notice instead of leaving them on a screen where everything fails.
- Wrong username and wrong password produce the identical 401 message, so the form can't be used to discover usernames.
- 5 failed logins on one username locks that username for 60 seconds (in-memory; fine for a single-instance MVP).
- Accounts are created only by administrators: through the CLI or the admin-only `/admin/users` routes. Both call the same `create_account()` in `accounts.py`, so username and password rules can't differ between them. There is no public sign-up.
- Changing your password signs out every other session for that account, and wrong "current password" guesses count toward the same 5-strikes lockout as login.
- Admin routes sit behind a `require_admin` dependency (403 for everyone else) and return only counts, never file contents or password hashes. An admin can't delete their own account, which also protects the last administrator.

## Hardening and deployment (week 4)
- One middleware adds `nosniff`, `X-Frame-Options: DENY`, `no-referrer` and `no-store` to every response.
- Each account has a storage quota (default 200 MB). The check happens on the server, so editing the browser can't get around it; the client also checks the 25 MB per-file limit first so a too-big file never starts uploading.
- Allowed browser origins come from `CERBERUS_CORS_ORIGINS` instead of being hardcoded.
- The client picks its API address in `core/api-base.ts`: `ng serve` (port 4200) talks to port 8000 directly, anything else uses `/api` on its own origin. In Docker, nginx serves the built client and forwards `/api/` to the backend, so the browser only ever talks to one origin. See `docs/DEPLOY.md`.
- GitHub Actions (`.github/workflows/ci.yml`) runs the backend tests and the client build and unit tests on every push.

## Signed-in devices and renaming (week 5)
- A login is one row in `sessions`. The Account page lists the caller's live rows. The public id of a row is the first 16 hex characters of the SHA-256 of its token: enough to tell rows apart, useless for logging in. No database change was needed, so existing databases keep working.
- Sessions are looked up only through the caller's own rows, so revoking someone else's id is just a `404`. The caller's current session can't be revoked from the list (that's what Log out is for), so nobody locks themselves out by accident.
- `POST /auth/logout-others` is the same cleanup `change-password` already did, available on its own.
- Renaming changes only `files.filename`. The file's identity is the SHA-256 of its ciphertext, which doesn't change, so downloads and decryption are unaffected. The browser checks the name first (same rules as the server) and doesn't send a request when the name is unchanged.

## Known limits (MVP)
- No password recovery: lose a file's password and the file is gone. The UI says so before upload.
- Max upload is 25 MB (whole file is encrypted in memory in the browser).
- File names and sizes are visible to the server; only contents are encrypted.
- Login rate limiting resets if the server restarts.
- Sessions have a fixed lifetime from login; there is no idle-timeout sliding window or "remember me".

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | /auth/login | username + password -> session token |
| POST | /auth/logout | end the session (idempotent) |
| GET | /files | metadata for the caller's files |
| POST | /file/upload | store an encrypted blob |
| GET | /file/{hash} | return an encrypted blob (owner only) |
| DELETE | /file/{hash} | permanently delete a stored blob (owner only) |
| GET | /health | server + database check |
| GET | /me/storage | how much of your storage quota is used |
| POST | /auth/change-password | change your sign-in password; signs out your other sessions |
| GET | /admin/users | (admin) accounts with file counts and storage |
| POST | /admin/users | (admin) create an account |
| DELETE | /admin/users/{id} | (admin) delete an account, its files and sessions |
