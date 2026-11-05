# Shelfie (A): reverse-engineering report

App id: A · Access: own-code · Licence: none (the user's own code) · Code reuse: allowed
Slice studied: library, ratings, export · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented** (README, docs, OpenAPI spec),
**inferred** (deduced, not seen), or **unknown**. The structured version is
`source.json` in the same folder. The code was read, never run (not approved).

## Summary

Shelfie is a 34-line, single-process Python JSON API (standard-library
`http.server`, SQLite) that lists books, takes 1-5 star ratings and exports
titles with ratings as JSON. Its documentation is out of date and disagrees
with the code on eight points: CSV vs JSON export, 1-10 vs 1-5 ratings,
`score` vs `stars`, `/api/v1` vs `/api`, PostgreSQL vs SQLite, three services
vs one process, and gateway auth vs no auth. Per the user ("trust what the
apps actually do") and the skill's rule, the code wins everywhere. There is
no UI, no auth, no way to add books, and no commit of writes (inferred).

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | sources/shelfie | 2026-11-04 | not a git repo; scan clean; 4 files, all read |
| A-R02 | documentation | sources/shelfie/README.md | 2026-11-04 | outdated; contradicted by code |
| A-R03 | documentation | sources/shelfie/docs/architecture.md | 2026-11-04 | outdated; contradicted by code |
| A-R04 | api-spec | sources/shelfie/openapi.yaml | 2026-11-04 | outdated; contradicted by code |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `app.py:6` | books(id, title not null, author) |
| A-E02 | A-R01 | observed | `app.py:13-15` | GET /api/books lists all books as JSON |
| A-E03 | A-R01 | observed | `app.py:7-8` | ratings(book_id, stars CHECK 1-5) |
| A-E04 | A-R01 | observed | `app.py:20-27` | PUT /api/books/{id}/rating, field `stars`, 1-5, 400 otherwise, appends |
| A-E05 | A-R01 | observed | `app.py:16-18` | GET /api/books/export returns JSON {title, stars} |
| A-E06 | A-R01 | observed | `app.py:1-4` | SQLite, SHELFIE_DB |
| A-E07 | A-R01 | observed | `app.py:5` | SHELFIE_SESSION_SECRET required, unused |
| A-E08 | A-R01 | observed | `app.py:2-34` | one HTTPServer process on 8080 |
| A-E09 | A-R01 | observed | `app.py:11-30` | no auth, no commit, no 404, no book create |
| A-E10 | A-R02 | documented | `README.md:3` | claims CSV export at /api/v1/books/export.csv |
| A-E11 | A-R02 | documented | `README.md:4` | claims 1-10 ratings |
| A-E12 | A-R02 | documented | `README.md:5` | claims PostgreSQL |
| A-E13 | A-R02 | documented | `README.md:6` | claims three services |
| A-E14 | A-R03 | documented | `docs/architecture.md:3-4` | claims gateway with auth, a DB per service |
| A-E15 | A-R04 | documented | `openapi.yaml:4-5` | claims GET /api/v1/books |
| A-E16 | A-R04 | documented | `openapi.yaml:6-7` | claims GET /api/v1/books/export.csv |
| A-E17 | A-R04 | documented | `openapi.yaml:8-11` | claims `score` 1-10 |
| A-E18 | A-R01 | inferred | `app.py:7-26` | FKs unenforced and writes uncommitted (sqlite3 defaults) |

### Documentation vs code

| Id | Documented | Code (wins) | Resolution |
| --- | --- | --- | --- |
| A-C01 | README: CSV export (A-E10) | JSON export (A-E05) | JSON; CSV is an unbuilt claim |
| A-C02 | Spec: /api/v1/books/export.csv (A-E16) | /api/books/export JSON (A-E05) | as A-C01 |
| A-C03 | README: 1-10 (A-E11) | 1-5 (A-E04) | 1-5 stars |
| A-C04 | Spec: `score` 1-10 (A-E17) | `stars` 1-5 (A-E04) | `stars`, 1-5 |
| A-C05 | Spec: /api/v1/books (A-E15) | /api/books (A-E02) | no version prefix |
| A-C06 | README: PostgreSQL (A-E12) | SQLite (A-E06) | SQLite |
| A-C07 | README: three services (A-E13) | one process (A-E08) | one process |
| A-C08 | Docs: gateway auth, DB per service (A-E14) | no auth, one DB (A-E09) | no auth; secret unused |

## Features

### A-F01 Browse the book library

- **Source application:** Shelfie (A)
- **Evidence:** A-E01, A-E02, A-E09
- **Description:** list every book with title and author.
- **Observed behaviour:** GET /api/books returns all books as JSON, unpaged, no auth.
- **Business logic:** title required, author optional. No create/edit/delete endpoint.
- **Data requirements:** Book.
- **Dependencies:** none.
- **Integration requirements:** a way to add books; per-user ownership.
- **Basis and confidence:** observed, high

### A-F02 Rate a book (1-5 stars)

- **Source application:** Shelfie (A)
- **Evidence:** A-E03, A-E04 (docs claim 1-10: A-E11, A-E17, contradicted)
- **Description:** rate a book 1 to 5 stars.
- **Observed behaviour:** PUT /api/books/{id}/rating {"stars": n}; 400 outside 1-5; inserts a new row each time.
- **Business logic:** integer 1..5 in handler and CHECK; appended; no user.
- **Data requirements:** Rating, Book.
- **Dependencies:** A-F01.
- **Integration requirements:** one rating per user per book in the unified app.
- **Basis and confidence:** observed, high

### A-F03 Export library with ratings (JSON)

- **Source application:** Shelfie (A)
- **Evidence:** A-E05 (docs claim CSV: A-E10, A-E16, contradicted)
- **Description:** download titles with their star ratings as JSON.
- **Observed behaviour:** GET /api/books/export returns [{title, stars}] from a left join; unrated → null; multiply-rated books repeat.
- **Business logic:** JSON only; title and stars only.
- **Data requirements:** Book, Rating.
- **Dependencies:** A-F01, A-F02.
- **Integration requirements:** unified Book and Rating.
- **Basis and confidence:** observed, high

## Screens and workflows

None: Shelfie has no UI (observed, A-E08). No screens or workflows.

## Navigation

None (JSON API only).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Book | id (integer) | title (text, required), author (text) | - | observed | A-E01 |
| Rating | none (rowid) | book_id (integer), stars (integer 1-5) | book_id → Book (not enforced) | observed | A-E03, A-E18 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/books` | none | - | [{id, title, author}] | - | A-E02 |
| GET | `/api/books/export` | none | - | [{title, stars}] | - | A-E05 |
| PUT | `/api/books/{id}/rating` | none | {stars: 1-5} | {ok: true} | 400 {error} | A-E04 |

The documented `/api/v1/...` paths and CSV endpoint do not exist (A-C01..A-C05).

## Authentication and authorization

None (observed, A-E09). SHELFIE_SESSION_SECRET is required at startup but never used (A-E07). The documented gateway auth does not exist (A-C08).

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| none | | | |

## Architecture and stack

Single Python 3 process, standard-library `http.server`, SQLite via `sqlite3`, no third-party packages (observed, A-E06, A-E08). The documented three services and PostgreSQL do not exist (A-C06, A-C07).

## Configuration

- `SHELFIE_DB`: SQLite file path (default shelfie.db).
- `SHELFIE_SESSION_SECRET`: required, undocumented, unused. Value never recorded.

## Error handling

- stars out of range → 400 `{"error": "stars must be 1 to 5"}` (observed).
- missing/invalid body or id → unhandled exception, connection dropped (inferred from code path).
- unknown path → no response (observed).
- rating for missing book → accepted (inferred, FKs off).

## Unknowns

- CSV export: documented only, contradicted by the code; not treated as a feature.
- 1-10 scale, `score` field, `/api/v1` prefix: documented only, contradicted.
- PostgreSQL and the three-service gateway: documented only, contradicted.
- Purpose of SHELFIE_SESSION_SECRET.
- How books are added (no endpoint).
- Whether writes persist (no commit; inferred, not run).
- Whether multiple ratings per book are intended.
- Exact Python version.
