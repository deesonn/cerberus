# Cerberus API reference

Every route the FastAPI server in `backend/app/main.py` exposes, what it does, and what it answers.
Routes marked **login** need an `Authorization: Bearer <token>` header (the token comes from `/auth/login`).
Routes marked **admin** need a token that belongs to an administrator.

| Method | Path | Who | What it does |
|---|---|---|---|
| GET | `/health` | anyone | Runs `SELECT 1` against the database. `200 {"status":"ok"}` proves the server *and* the database are up. |
| POST | `/auth/login` | anyone | Body `{username, password}`. Checks the bcrypt hash, creates a random session token and returns `{token, username, is_admin}`. |
| POST | `/auth/logout` | anyone | Deletes the caller's session row so the token stops working. Always `200`, even if the session was already gone. |
| POST | `/auth/change-password` | login | Body `{current_password, new_password}`. See below. |
| GET | `/files` | login | Metadata (name, size, date, hash) of the caller's files only. Never contents. |
| POST | `/file/upload` | login | Stores the encrypted blob the browser sends (max 25 MB) and returns its SHA-256 hash. |
| GET | `/file/{hash}` | login | Returns the stored ciphertext, but only to the file's owner. |
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

## Status codes at a glance

`200` ok / `201` created / `400` not allowed on yourself / `401` not signed in or session expired / `403` signed in but not allowed (wrong current password, or not an admin) / `404` not found (also used when a file belongs to someone else) / `409` username already taken / `413` upload too large / `422` input failed validation / `429` too many failed attempts.
