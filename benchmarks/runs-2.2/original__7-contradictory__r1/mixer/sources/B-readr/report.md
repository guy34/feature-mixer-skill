# Readr (B): reverse-engineering report

App id: B · Access: own-code · Licence: none stated (the user's own code) · Code reuse: allowed
Slice studied: reading lists and ratings · Coverage: complete · Size: S

Basis marks: **observed** (read in the code; nothing was run), **inferred**, **unknown**. Structured version: `source.json`.

## Summary

Readr is a 16-line Python module over SQLite with two functions: `rate(book_id, stars)` (1-5 stars, checked in
code only) and `add_to_list(list_id, book_id)`. It has books (title only), named lists and a list-book join
table. Nothing creates lists or books, reads data back, or exposes an interface; writes are never committed;
there are no users. No documentation exists, so there is nothing to contradict.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | sources/readr | 2026-11-04 | `readr.py` read in full; scan clean |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `readr.py:1` | header: reading lists and 1-5 star ratings |
| B-E02 | B-R01 | observed | `readr.py:2-4` | SQLite readr.db; books(id, title) |
| B-E03 | B-R01 | observed | `readr.py:5-7` | lists(id, name), list_books(list_id, book_id), no uniqueness |
| B-E04 | B-R01 | observed | `readr.py:8` | ratings(book_id, stars), no CHECK, no key |
| B-E05 | B-R01 | observed | `readr.py:10-13` | rate() rejects outside 1-5, appends |
| B-E06 | B-R01 | observed | `readr.py:15-16` | add_to_list() inserts without checks |
| B-E07 | B-R01 | observed | `readr.py:1-16` | no create/read/remove, no entry point, no commit, no auth |

## Features

### B-F01 Reading lists

- **Source application:** Readr (B)
- **Evidence:** B-E03, B-E06, B-E07
- **Description:** put books on named reading lists.
- **Observed behaviour:** `add_to_list` appends a row; nothing creates, shows or edits lists.
- **Business logic:** list name required; duplicates allowed; no existence checks.
- **Data requirements:** List, ListBook, Book.
- **Dependencies:** none.
- **Integration requirements:** books from the shared library; list ownership.
- **Basis and confidence:** observed, medium (only part of the feature exists).

### B-F02 Rate a book (1-5 stars)

- **Source application:** Readr (B)
- **Evidence:** B-E01, B-E04, B-E05
- **Description:** give a book 1 to 5 stars.
- **Observed behaviour:** `rate` raises ValueError outside 1-5, else appends a row.
- **Business logic:** 1..5 in code only; appends.
- **Data requirements:** Rating(book_id, stars).
- **Dependencies:** none.
- **Integration requirements:** Book.
- **Basis and confidence:** observed, high.

## Screens and workflows

None (no UI or entry point).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Book | id (integer) | title (text, required) | - | observed | B-E02 |
| List | id (integer) | name (text, required) | - | observed | B-E03 |
| ListBook | none | list_id (integer), book_id (integer) | → List, → Book | observed | B-E03 |
| Rating | none | book_id (integer), stars (integer) | → Book | observed | B-E04 |

## API

None: functions only (`rate`, `add_to_list`).

## Authentication and authorization

None.

## Architecture and stack

Python 3 module, standard library `sqlite3`, hard-coded `readr.db`. No packages.

## Configuration

None (file name hard-coded).

## Error handling

`rate` raises ValueError outside 1-5. `add_to_list` accepts anything. No commit (writes lost on close; inferred).

## Unknowns

- What created lists and books and read them back (no code for it).
- Whether a `readr.db` with real data exists.
- Runtime behaviour not observed (running source code not approved).
