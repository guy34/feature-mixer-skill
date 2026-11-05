# Module summary: docs (A Shelfie)

Index: `index.json` · Files: 1 · Lines: 4 · Read on: 2026-11-04 · Files read: 1 of 1

## Purpose

`docs/architecture.md` describes a three-service design (catalog, ratings, gateway with auth), each with its own database.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| none | `docs/architecture.md` | architecture claim only; contradicted by `app.py` (one process, one SQLite file, no auth) |

## Depends on

Modules: none. External packages: none.

## Entry points and important files

- `docs/architecture.md`: stale architecture description (evidence A-E13).

## Not read, and why

- none

## Open questions

- Whether the three-service design was ever built anywhere.
