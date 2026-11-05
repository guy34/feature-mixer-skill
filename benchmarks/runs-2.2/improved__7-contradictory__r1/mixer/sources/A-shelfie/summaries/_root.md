# Module summary: (root) (A Shelfie)

Index: `index.json` · Files: 3 · Lines: 51 · Read on: 2026-11-04 · Files read: 3 of 3

## Purpose

The whole Shelfie app (`app.py`) plus its README and OpenAPI spec. The docs are out of date; the code is the behaviour.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F01 | `app.py:6,13-15` | list books; no create/edit/delete endpoint |
| A-F02 | `app.py:7-8,20-27` | 1-5 stars (docs say 1-10, field 'score'); appends |
| A-F03 | `app.py:16-18` | JSON export (docs say CSV) |

## Depends on

Modules: none. External packages: standard library only (http, json, os, sqlite3).

## Entry points and important files

- `app.py`: HTTPServer on port 8080; requires SHELFIE_SESSION_SECRET (unused) and optional SHELFIE_DB.
- `README.md`, `openapi.yaml`: claims contradicted by app.py (A-C01..A-C07).

## Not read, and why

- none

## Open questions

- How books are added; whether ratings were meant to be appended; what the secret was for.
