# Module summary: (root) (A QuickNotes)

Index: `index.json` · Files: 3 · Lines: 28 · Read on: 2026-11-04 · Files read: 3 of 3

## Purpose

The whole app: SQL schema plus a Python module of HTTP handlers and a route table.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F01 | `schema.sql`, `app.py` | CRUD, newest first |
| A-F02 | `schema.sql`, `app.py` | shared tags, many-to-many |
| A-F03 | `app.py` | LIKE on title or body |
| A-F04 | `app.py` | markdown.render |

## Depends on

Modules: none. External packages: markdown.

## Entry points and important files

- `app.py`: handlers and ROUTES
- `schema.sql`: the data model

## Not read, and why

- none

## Open questions

- The `db` helper is not in the folder.
