# Spendly (B): reverse-engineering report

App id: B · Access: own-code · Licence: user's own code (no licence file) · Code reuse: allowed
Slice studied: categories and adding an expense (the whole app) · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the running app, a screenshot or the code),
**documented** (official docs or a published spec), **inferred** (deduced,
not seen), or **unknown**. The structured version of this report is
`source.json` in the same folder.

## Summary

Spendly is the user's own six-line Python module. It holds a fixed list of
four categories and an `add()` function that records an expense (amount in
cents, category, optional note) in an in-memory list, rejecting unknown
categories. There is no persistence, UI, users, currency, date or id. All
of it was read (observed); nothing was run.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | sources/spendly | 2026-11-04 | 1 file, scanned clean, indexed, read in full, not run |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `spendly.py:1` | Categories: food, travel, home, other |
| B-E02 | B-R01 | observed | `spendly.py:2` | Expenses in an in-memory list |
| B-E03 | B-R01 | observed | `spendly.py:3` | add(amount_cents, category, note="") |
| B-E04 | B-R01 | observed | `spendly.py:4` | Unknown category raises ValueError; amount unchecked |

## Features

### B-F01 Add an expense

- **Source application:** Spendly (B)
- **Evidence:** B-E02, B-E03, B-E04
- **Description:** record amount (cents), category and optional note.
- **Observed behaviour:** validates category, appends a dict to `EXPENSES`.
- **Business logic:** integer cents by name only; amount not validated; no currency, date, id or owner.
- **Data requirements:** amount_cents, category, note.
- **Dependencies:** B-F02.
- **Integration requirements:** persistence, ids, dates, owner, currency.
- **Basis and confidence:** observed, high

### B-F02 Fixed expense categories

- **Source application:** Spendly (B)
- **Evidence:** B-E01, B-E04
- **Description:** exactly food, travel, home, other; anything else is rejected.
- **Observed behaviour:** `CATEGORIES` constant; membership check in `add()`.
- **Business logic:** case-sensitive membership check; no custom categories; `other` is the catch-all.
- **Data requirements:** category.
- **Dependencies:** none.
- **Integration requirements:** one category vocabulary for every expense.
- **Basis and confidence:** observed, high

## Screens and workflows

None: Spendly has no user interface.

## Navigation

None.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Expense | none | amount_cents (int), category (str), note (str) | none | observed | B-E02, B-E03 |

## API

None (a Python function, `add()`).

## Authentication and authorization

None.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| none | | | |

## Architecture and stack

One Python module, standard library only, no dependencies, in-memory state (observed).

## Configuration

None.

## Error handling

Unknown category: `ValueError("unknown category")`. Invalid amounts are
accepted silently.

## Unknowns

- None for this slice: the whole app was read.
