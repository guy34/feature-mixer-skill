# Module summary: (root) (B OpenForum)

Index: `index.json` · Files: 3 · Lines: 25 · Read on: 2026-11-04 · Files read: 3 of 3

## Purpose

The whole OpenForum slice: Python API functions, models described in comments, and the MIT licence.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| B-F01 | `api.py` | JWT with a literal signing key (scan: medium) |
| B-F02 | `api.py`, `models.py` | 10000-character limit |
| B-F03 | `api.py`, `models.py` | no status: live at once |
| B-F04 | `api.py`, `models.py` | author_id null = anonymous |
| B-F05 | `api.py` | no auth on read |
| B-F06 | `api.py` | client route only |

## Depends on

Modules: none. External packages: jwt (PyJWT, version not declared).

## Entry points and important files

- `api.py`: handlers and route table
- `models.py`: schema in comments, constants
- `LICENSE`: MIT

## Not read, and why

- none: all three files read

## Open questions

- PyJWT version, framework, db layer, admin powers (see source.json unknowns)
