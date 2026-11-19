# Cerberus API reference

Every route the FastAPI server in `backend/app/main.py` exposes, what it does, and what it answers.
Routes marked **login** need an `Authorization: Bearer <token>` header (the token comes from `/auth/login`).
Routes marked **admin** need a token that belongs to an administrator.

| Method | Path | Who | What it does |
|---|---|---|---|
| GET | `/health` | anyone | Runs `SELECT 1` against the database. `200 {"status":"ok"}` proves the server *and* the database are up. |
| POST | `/auth/login` | anyone | Body `{username, password}`. Checks the bcrypt hash, creates a random session token and returns `{token, username, is_admin}`. |
| POST | `/auth/logout` | anyone | Deletes the caller's session row so the token stops working. Always `200`, even if the session was already gone. |
| GET | `/auth/sessions` | login | Every live login on the caller's account: `{id, created_at, expires_at, current}`. `id` is a short hash of the token, so the list never reveals a token. |
| DELETE | `/auth/sessions/{id}` | login | Signs out one other device. `404` if the id isn't one of the caller's live sessions (so another user's id looks the same as a made-up one). `400` if it is the caller's own current session. |
| POST | `/auth/logout-others` | login | Signs out every device on the account except the caller's. Returns `{signed_out: n}`. |
| POST | `/auth/change-password` | login | Body `{current_password, new_password}`. See below. |
| GET | `/files` | login | Metadata (name, size, date, hash) of the caller's files only. Never contents. |
| GET | `/me/storage` | login | `{used_bytes, quota_bytes, file_count, max_upload_bytes}` for the caller only. Sizes, never contents. Feeds the usage bar. |
| POST | `/file/upload` | login | Stores the encrypted blob the browser sends (max 25 MB per file, and the caller's total must stay under the storage quota) and returns its SHA-256 hash. |
| GET | `/file/{hash}` | login | Returns the stored ciphertext, but only to the file's owner. |
| PATCH | `/file/{hash}` | login | Body `{filename}`. Renames one of the caller's own files. Only the display name changes: the encrypted bytes and the hash stay the same. `404` for a missing or someone else's file, `422` for a bad name. |
| DELETE | `/file/{hash}` | login | Permanently deletes one of the caller's own files. |
| GET | `/admin/users` | admin | Every account with `file_count` and `total_bytes`. See below. |
| POST | `/admin/users` | admin | Creates an account. See below. |
| DELETE | `/admin/users/{id}` | admin | Deletes an account, its files and its sessions. See below. |

## How a request is checked

Two FastAPI dependencies do the gatekeeping, so individual routes don't repeat the checks:

1. `current_user` reads the bearer token, looks up its session, and rejects it with `401` if the token is missing, unknown, or older than 8 hours (`401 "Session expired"`; an expired session row is deleted on the spot).
2. `require_admin` runs `current_user` first and then answers `403 "Administrator access required"` unless `user.is_admin` is true.

## POST /auth/change-password

1. Needs a valid session (`401` otherwise).
2. Asks the shared lockout counter whether this username is locked (`429` if it already has 5 recent failures). The counter is the same one `/auth/login` uses, so someone holding a stolen token can't use this route to guess the old password.
3. Checks `current_password` against the stored bcrypt hash. Wrong -> counts as a failure and answers `403 "Current password is incorrect"`.
4. Checks the new password: at least 8 characters, and different from the current one (`422` otherwise).
5. Stores a new bcrypt hash for the user.
6. Deletes every session for this user **except the one making the request**, so any other browser or device is signed out and a leaked old token dies. Returns `{"status":"password changed","other_sessions_signed_out": N}`.

This only changes the sign-in password. Files stay encrypted with the password chosen at upload time, which the server never sees, so no stored file is affected.

## GET /admin/users

One SQL query joins `users` to `files` and groups by user, so each row is `{id, username, is_admin, file_count, total_bytes}`, sorted by username. The response is built from exactly those five fields, so password hashes and file names can't leak through it.

## POST /admin/users

Body `{username, password, is_admin?}`; answers `201 {id, username, is_admin}`. It calls `create_account()` in `accounts.py`, the same function the command-line tool uses, so the rules are identical everywhere:

* username trimmed, 3-32 characters of letters, digits, `.`, `_`, `-` (`422` otherwise)
* password at least 8 characters (`422`)
* username must be unused, compared case-insensitively so `Daniel` can't sit next to `daniel` (`409`)
* the password is stored only as a bcrypt hash

## DELETE /admin/users/{id}

1. `404` if that user doesn't exist.
2. `400 "You can't delete your own account"` if the admin targets themselves. A side effect is that the last administrator can never be deleted by accident.
3. Otherwise deletes the user's files, then their sessions (so any open browser is signed out immediately), then the user, and returns `{"status":"deleted","username":...,"files_removed":N}`.

## Filenames

Upload and rename share one set of rules (`_clean_filename` in `main.py`): spaces at either end are trimmed, the name can't be empty, can't be longer than 255 characters, and can't contain `/`, `\\` or control characters. Anything else answers `422` with a plain message. Two files may have the same name, because a file is identified by its hash.

## Security headers

Every response, errors included, carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` and `Cache-Control: no-store`. They're added by one middleware in `main.py` (`add_security_headers`), so no route can forget them.

## Storage quota

`POST /file/upload` adds the new blob's size to what the caller already stores. If the total would pass `CERBERUS_QUOTA_MB` (default 200) it answers `413 "Storage limit reached (N MB). Delete a file to make room."` and saves nothing. Filling the quota exactly is allowed. A duplicate file is reported (`409`) before the quota is checked. Every account has its own quota.

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `CERBERUS_DB_URL` | `sqlite:///./cerberus.db` | Database location |
| `CERBERUS_SESSION_HOURS` | `8` | How long a login lasts |
| `CERBERUS_QUOTA_MB` | `200` | Storage each account may use |
| `CERBERUS_CORS_ORIGINS` | `http://localhost:4200` | Comma-separated browser origins allowed to call the API |

## Status codes at a glance

`200` ok / `201` created / `400` not allowed on yourself / `401` not signed in or session expired / `403` signed in but not allowed (wrong current password, or not an admin) / `404` not found (also used when a file belongs to someone else) / `409` username already taken / `413` upload too large or storage quota reached / `422` input failed validation / `429` too many failed attempts.
