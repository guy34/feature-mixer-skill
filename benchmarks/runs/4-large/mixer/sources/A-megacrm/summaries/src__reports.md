# Module summary: src/reports (A MegaCRM)

Index: `index.json` · Files: 1 · Lines: 8 · Read on: 2026-11-04 · Files read: 1 of 1

## Purpose

CSV export of a whole table.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F04 | `src/reports/export.py` | export_csv(path, what='deals'); no header row; table name from the caller |

## Depends on

Modules: src/shared. External packages: none (standard library csv).

## Entry points and important files

- `src/reports/export.py`: export_csv.

## Not read, and why

- none

## Open questions

- Should exports include a header row and filters?
