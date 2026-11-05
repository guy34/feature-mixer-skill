# Spendly (B): reverse-engineering report

App id: B · Access: own-code · Licence: the user's own code (no licence file) · Code reuse: allowed
Slice studied: expense categories and the expense record they apply to · Coverage: complete · Size: S

Basis: everything here is **observed** in the code (`sources/spendly/spendly.py`, 6 lines, the only file).
Nothing was run. The structured version is `source.json`.

## Summary

Spendly is the user's own minimal expense recorder: one Python function adds an expense (amount in cents,
category, optional note) to an in-memory list after checking the category against a fixed list of four. There
is no UI, storage, user, currency or date. The part the user wants is the category model: a small fixed set
(food, travel, home, other) that every expense must use.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | `sources/spendly` | 2026-11-04 | 1 file, scanned (no findings) and indexed |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `spendly.py:1` | categories: food, travel, home, other |
| B-E02 | B-R01 | observed | `spendly.py:2` | in-memory list, no persistence |
| B-E03 | B-R01 | observed | `spendly.py:3-6` | add() rejects unknown categories, stores amount_cents, category, note |

## Features

### B-F01 Record an expense

- **Source application:** Spendly (B) · **Evidence:** B-E02, B-E03
- **Description / behaviour:** add an expense in integer cents with a category and optional note.
- **Business logic:** category required and validated; amount not validated.
- **Dependencies:** B-F02 · **Basis and confidence:** observed, high

### B-F02 Expense categories

- **Source application:** Spendly (B) · **Evidence:** B-E01, B-E03
- **Description / behaviour:** fixed categories food, travel, home, other; anything else raises `ValueError("unknown category")`.
- **Business logic:** exact, case-sensitive match; "other" is the catch-all; no user-defined categories.
- **Basis and confidence:** observed, high

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Expense | none | amount_cents (int, cents), category (str, one of 4), note (str, default "") | none | observed | B-E02, B-E03 |

## API

None: a Python function, `add(amount_cents, category, note="")`.

## Authentication and authorization

None.

## Architecture and stack

Python standard library only, single module, no storage. Module summary: `summaries/_root.md`.

## Error handling

Unknown category raises ValueError and nothing is stored. Amounts are not validated.

## Unknowns

- No currency, date, merchant, owner or id on an expense.
- No persistence, so no existing data to migrate (to confirm with the user).
- No UI or entry point in the folder.
