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
- Accounts are created only through the admin CLI, never through the web app.

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
