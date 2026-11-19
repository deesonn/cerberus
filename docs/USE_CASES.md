# Use Case Narratives - CPSC 49200

## Team and Project

- **Project Name** - Cerberus
- **Team Name** - Solo project (no team name)
- **Team Members**
  - Daniel Nguyen, danielnguyen@lewisu.edu, skilled in full-stack development (Python/FastAPI backend, Angular frontend), applied encryption/security implementation, and database design, with direct exposure to sensitive-data handling from six years as a licensed real estate broker.

## Use case narratives

We now present the features of the minimum viable product (MVP) version
of this project as a set of use case narratives. Each use case narrative
starts with a title that identifies the user and how they will use the
system. Then the narrative will describe the details of that interaction,
including exceptional circumstances that may arise. If two different kinds
of roles exercise a particular feature differently, those are presented
here as two use case narratives.

We will list these use case narratives as a set of checkboxes, since
they are features we will check off as we complete their implementation.

- [x] 1. **User registers a new account.**
  A new user visits the registration screen and submits a username and a
  password. The system checks that the username isn't already taken and
  that the password meets a minimum strength requirement, then creates the
  account. The password itself is never stored — the system stores only a
  securely salted hash of it, so the account can be verified on future
  logins without the system ever holding a copy of the plaintext password.
  Once the account is created, the user is shown a confirmation and can
  proceed to log in. *Exceptional circumstances:* if the chosen username is
  already taken, the system rejects the request and tells the user to pick
  a different one; if the password doesn't meet the minimum strength
  requirement, the system explains what's missing (length, character
  variety, etc.) and asks the user to try again without discarding the
  username they entered.

- [x] 2. **User logs in to access their account.**
  A returning user enters their username and password on the login screen.
  The system looks up the username, hashes the submitted password using the
  same method used at registration, and compares it against the stored
  hash. On a match, the system starts an authenticated session and takes
  the user to their file list. *Exceptional circumstances:* if the username
  doesn't exist or the password doesn't match, the system shows a generic
  "invalid username or password" message rather than revealing which one
  was wrong, so an attacker can't use the error message to guess valid
  usernames. After several consecutive failed attempts on the same account,
  the system temporarily rate-limits further login attempts against it to
  slow down brute-force guessing.

- [x] 3. **User logs out of their session.**
  A logged-in user selects "log out" from the client. The system ends the
  user's authenticated session immediately, so that any further attempt to
  access file endpoints from that browser session is rejected until the
  user logs in again. This matters especially on a shared computer, where a
  user needs confidence that closing out their session actually revokes
  access rather than leaving it open. *Exceptional circumstances:* if the
  logout request is sent after the session has already expired or been
  invalidated (e.g. the user was idle long enough to time out), the system
  simply confirms the user is logged out rather than returning an error, so
  the user isn't confused by a failure message for an action that already
  effectively happened.

- [x] 4. **User uploads and encrypts a file.**
  A logged-in user selects a file from their device and enters a password
  to protect it (which may be the same as or different from their login
  password). The Angular client encrypts the file locally, in the browser,
  using a key derived from that password, before ever sending anything to
  the server. The server receives and stores only the resulting ciphertext,
  tagged with the uploading user's account, and confirms the upload to the
  user. Because encryption happens client-side, the server and its
  administrators never have access to the file's plaintext contents.
  *Exceptional circumstances:* if the upload is interrupted (e.g. a network
  drop mid-transfer), the system detects the incomplete upload and reports
  the failure to the user rather than saving a corrupted, unusable file; if
  no encryption password is entered, the client blocks the upload and
  prompts the user to provide one.

- [x] 5. **User views a list of their uploaded files.**
  A logged-in user navigates to their file list. The system retrieves the
  metadata (filename, upload date) for every file tied to that user's
  account and displays it, without decrypting or exposing any file
  contents at this stage — listing a file never requires the encryption
  password. *Exceptional circumstances:* if the user has no files yet, the
  system shows a friendly empty state (e.g. "You haven't uploaded any files
  yet") rather than a blank or broken-looking screen.

- [x] 6. **User downloads and decrypts a file.**
  A logged-in user selects a file from their list and enters the password
  that was used to encrypt it. The client downloads the stored ciphertext
  from the server and decrypts it locally using a key derived from the
  entered password, then makes the resulting plaintext file available to
  the user. *Exceptional circumstances:* if the user enters the wrong
  password, decryption fails in a detectable way (rather than silently
  producing garbage output), and the system tells the user the password
  was incorrect and lets them try again; because the server never has the
  password or the key, there is no "reset" path if the password is truly
  lost, and the user is warned of this at upload time.

- [x] 7. **Administrator creates a new administrator account via the CLI tool.**
  An existing administrator runs the command-line admin tool from a
  terminal with server/database access and issues a command to create a
  new administrator account, supplying a username and password for the new
  admin. The CLI tool hashes the password the same way the web application
  does and writes the new account directly to the database with elevated
  (administrator) privileges. The CLI is the way in even when nobody can
  use the website, for example to create the very first administrator.
  Administrators can also create accounts from the Admin page of the web
  app (use case 10), which is only reachable with an administrator login
  and follows the exact same account rules as the CLI.
  *Exceptional circumstances:* if the requested username already exists,
  the CLI tool rejects the command and reports the conflict instead of
  overwriting the existing account; if the tool is run without the
  necessary database access/credentials, it fails clearly with a
  permissions error rather than silently doing nothing.

- [x] 8. **The system protects user credentials and stored files at rest.**
  Independent of any single user action, the system is responsible for
  ensuring that data at rest is never recoverable in plaintext by anyone
  with access to the server or database alone. Passwords are stored only
  as salted, algorithmically-hashed values (never reversible back to the
  original password), and uploaded files are stored only as ciphertext
  produced by client-side, password-derived encryption — the server itself
  never possesses the plaintext file, the encryption key, or the original
  password at any point after account creation or upload. *Exceptional
  circumstances:* if the database were ever compromised, the system's
  design goal is that an attacker would obtain only password hashes and
  encrypted file blobs — not usable credentials or readable files —
  meaning the practical damage of a server-side breach alone is
  significantly limited.

- [x] 9. **User changes their account password.**
  A logged-in user opens the Account page and enters their current
  password, a new password of at least eight characters, and the new
  password again to confirm it. The system checks the current password,
  stores a new salted hash, and signs out every other device that was
  logged in to the account, while the device being used stays signed in.
  This changes only the password used to log in; files keep the separate
  password they were encrypted with, so nothing already stored is affected.
  *Exceptional circumstances:* if the current password is wrong, nothing
  changes and the attempt counts toward the same lockout as logging in, so
  a stolen session can't be used to guess the password; if the new password
  is too short, doesn't match its confirmation, or is the same as the old
  one, the page says so before changing anything.

- [x] 10. **Administrator manages user accounts from the web app.**
  An administrator opens the Admin page, which lists every account with
  its role, how many files it holds and how much storage it uses (counts
  only, never file contents or password hashes). From there the administrator
  can create a new regular or administrator account, or delete an account
  together with its files and logins after a confirmation that says how many
  files will be removed. *Exceptional circumstances:* a regular user who
  opens the Admin page is sent back to their file list and the server
  refuses the underlying requests with a "forbidden" answer; a username
  that already exists (in any capitalization) or breaks the account rules is
  rejected with a clear message; an administrator can't delete their own
  account, which also means the last administrator can't be removed by
  accident.

- [x] 11. **User reviews where they are signed in and signs devices out.**
  A logged-in user opens the Account page and sees every browser or device
  currently signed in to their account, each with when it signed in and how
  long it has left, and with the current device clearly marked. The user can
  sign out one other device, or sign out all other devices at once. That
  matters when a login was left on a shared or lost computer: the user
  doesn't have to wait for it to expire. The list shows a short label for
  each login, never the login token itself. *Exceptional circumstances:*
  the current device has no "sign out" button (the Log out button is for
  that), so nobody locks themselves out by accident; a signed-out device is
  sent to the login page the next time it contacts the server; one user can
  never see or end another user's logins.

- [x] 12. **User renames an uploaded file.**
  From the file list a user chooses Rename on one of their files, edits the
  name in place and saves. The system changes only the name shown in the
  list and used when the file is downloaded; the encrypted contents are not
  touched, so the file still decrypts with the same password. *Exceptional
  circumstances:* an empty name, a name over 255 characters, or a name
  containing slashes or control characters is refused with a plain message
  (the browser checks first, and the server checks again); saving the name
  unchanged simply closes the editor; a user can't rename another user's
  file, and trying looks the same as asking about a file that doesn't exist.

- [x] 13. **The system limits how much one account can store.**
  Each account has a storage limit (200 MB by default, set by the server's
  administrator). The file list shows how much of it is used and the
  largest single file allowed (25 MB). A file over the per-file limit is
  refused in the browser before anything is encrypted or sent. An upload
  that would push the account over its storage limit is refused by the
  server with a message to delete a file to make room, and nothing is saved.
  Deleting a file frees the space immediately, and one account's files never
  count against another's. *Exceptional circumstances:* because the server
  enforces the limit itself, changing the web page can't get around it.
