# Readr (B): reverse-engineering report

App id: B · Access: own-code · Licence: none (the user's own code) · Code reuse: allowed
Slice studied: reading lists and ratings · Coverage: complete · Size: S

Basis marks as in the template: **observed** (seen in the code), **documented**,
**inferred**, **unknown**. Structured version: `source.json`. Code read, never run.

## Summary

Readr is a 16-line Python module: a SQLite schema for books (title only),
named reading lists, list membership and ratings, plus two functions,
`rate(book_id, stars)` (1-5, appended) and `add_to_list(list_id, book_id)`.
It has no UI, HTTP API or entry point, and no code to create, show or delete
lists or books. Its one-line header comment agrees with the code; there is no
other documentation, so no contradictions.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | sources/readr | 2026-11-04 | not a git repo; scan clean; 1 file, read in full |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | documented | `readr.py:1` | header comment: reading lists and 1-5 star ratings |
| B-E02 | B-R01 | observed | `readr.py:2-3` | SQLite readr.db; no commit |
| B-E03 | B-R01 | observed | `readr.py:4` | books(id, title not null) |
| B-E04 | B-R01 | observed | `readr.py:5` | lists(id, name not null) |
| B-E05 | B-R01 | observed | `readr.py:6-7` | list_books(list_id, book_id), duplicates possible |
| B-E06 | B-R01 | observed | `readr.py:8` | ratings(book_id, stars) no CHECK |
| B-E07 | B-R01 | observed | `readr.py:10-13` | rate(): 1..5 else ValueError; appends |
| B-E08 | B-R01 | observed | `readr.py:15-16` | add_to_list(): inserts, no validation |
| B-E09 | B-R01 | observed | `readr.py:1-16` | no UI/API/CLI; no list or book create/view/delete |

## Features

### B-F01 Rate a book (1-5 stars)

- **Source application:** Readr (B)
- **Evidence:** B-E01, B-E06, B-E07
- **Description:** rate a book 1 to 5 stars.
- **Observed behaviour:** rate() raises ValueError outside 1..5, else inserts a row.
- **Business logic:** 1..5 in code only; appended; no user.
- **Data requirements:** Rating, Book.
- **Dependencies:** none.
- **Integration requirements:** unified Book; same scale as Shelfie.
- **Basis and confidence:** observed, high

### B-F02 Reading lists

- **Source application:** Readr (B)
- **Evidence:** B-E04, B-E05, B-E08, B-E09
- **Description:** put books on named reading lists.
- **Observed behaviour:** add_to_list() inserts a membership row; nothing creates, shows, renames or deletes lists or removes books.
- **Business logic:** list name required; many-to-many; duplicates allowed; ids not validated.
- **Data requirements:** ReadingList, ListBook, Book.
- **Dependencies:** none.
- **Integration requirements:** list create/view/remove (absent), per-user ownership.
- **Subfeatures:** add to list (observed); create/view/rename/delete (schema only).
- **Basis and confidence:** observed, medium (only half the lifecycle is in code)

## Screens and workflows

None (no UI; B-E09).

## Navigation

None.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Book | id (integer) | title (text, required) | - | observed | B-E03 |
| ReadingList | id (integer) | name (text, required) | - | observed | B-E04 |
| ListBook | none | list_id (integer), book_id (integer) | → ReadingList, → Book | observed | B-E05 |
| Rating | none | book_id (integer), stars (integer) | → Book | observed | B-E06 |

## API

None: Python functions `rate(book_id, stars)` and `add_to_list(list_id, book_id)` only.

## Authentication and authorization

None (no users; B-E09).

## Integrations

None.

## Architecture and stack

Python 3 module, SQLite via `sqlite3`, no third-party packages, no entry point (observed).

## Configuration

None (database path hard-coded as readr.db).

## Error handling

- stars outside 1..5 → ValueError (observed).
- unknown list/book id → accepted (inferred, FKs off).

## Unknowns

- How lists and books are created, shown or deleted (no code).
- Whether writes persist (no commit; inferred, not run).
- Whether duplicate list entries and repeated ratings are intended.
- What calls the module.
- Exact Python version.
