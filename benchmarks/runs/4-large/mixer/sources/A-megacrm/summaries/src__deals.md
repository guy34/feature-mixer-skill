# Module summary: src/deals (A MegaCRM)

Index: `index.json` · Files: 2 · Lines: 9 · Read on: 2026-11-04 · Files read: 2 of 2

## Purpose

Sales pipeline with five fixed stages.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F03 | `src/deals/pipeline.py`, `src/deals/schema.sql` | STAGES lead/qualified/proposal/won/lost; ValueError on unknown stage |

## Depends on

Modules: src/shared. External packages: none.

## Entry points and important files

- `src/deals/pipeline.py`: STAGES, move_deal.
- `src/deals/schema.sql`: deals(id, contact_id -> contacts, title, value_cents, stage).

## Not read, and why

- none

## Open questions

- No owner, timestamps or transition rules on deals.
