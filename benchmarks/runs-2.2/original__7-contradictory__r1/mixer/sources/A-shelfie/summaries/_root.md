# Module summary: (root) (A Shelfie)

Index: `index.json` · Files: 3 · Lines: 51 · Read on: 2026-11-04 · Files read: 3 of 3

## Purpose

The whole app: `app.py` is a single-process JSON HTTP API over SQLite; `README.md` and `openapi.yaml` document it, but out of date.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F01 | `app.py:13-15`, `openapi.yaml` | list books; spec says /api/v1, code serves /api |
| A-F02 | `app.py:7-8,20-27`, `README.md:4`, `openapi.yaml` | code: stars 1-5; docs: score 1-10 |
| A-F03 | `app.py:16-18`, `README.md:3`, `openapi.yaml` | code: JSON at /api/books/export; docs: CSV at /api/v1/books/export.csv |

## Depends on

Modules: none. External packages: none (standard library `http.server`, `json`, `sqlite3`, `os`).

## Entry points and important files

- `app.py`: everything (schema, routes, validation); `SHELFIE_SESSION_SECRET` required but unused; no commit.
- `README.md`, `openapi.yaml`: contradict the code on format, scale, database and paths.

## Not read, and why

- none

## Open questions

- How books are added (no endpoint).
- What the unused session secret was for.
