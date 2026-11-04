# FileShare

Upload files (up to 10 MB), preview them (text, images) and share them through links that expire and can
need a password. Built by Feature Mixer from three of the user's own apps: Uploader (A), Previewer (B) and
ShareLink (C). Python 3 standard library only; no dependencies to install.

## Run

    python3 -m fileshare            # http://127.0.0.1:8000/

Settings are environment variables (see `.env.example`): `FILESHARE_DB`, `FILESHARE_HOST`,
`FILESHARE_PORT`, `FILESHARE_SECURE_COOKIE`.

## Test

    python3 -m unittest discover -s tests -t .

## Layout

- `fileshare/core/` database schema, HTTP helpers and error format, password hashing
- `fileshare/accounts.py` register, login, logout, sessions
- `fileshare/files.py` upload, list, delete, content; the ownership check
- `fileshare/preview.py` text / image / none previews
- `fileshare/sharing.py` share links: create, open, revoke, expiry, password
- `fileshare/web.py` routing and the two pages in `fileshare/static/`

Not production-ready: no rate limiting on login or link passwords, no HTTPS termination, and image
previews show the original image (no thumbnails).
