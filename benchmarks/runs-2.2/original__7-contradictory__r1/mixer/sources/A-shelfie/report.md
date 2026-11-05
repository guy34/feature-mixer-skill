# Shelfie (A): reverse-engineering report

App id: A · Access: own-code · Licence: none stated (the user's own code) · Code reuse: allowed
Slice studied: library, rating, export · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented** (README, docs, OpenAPI spec), **inferred**, or **unknown**.
The structured version is `source.json`. Nothing was run (not approved), so "observed" means read in the code.

## Summary

Shelfie is a tiny JSON HTTP API (one Python file, standard library only) over SQLite: list books, rate a
book 1-5 stars, export titles with ratings as JSON. **Its documentation is out of date and contradicts the
code on five points** (table below). As the user instructed, the code is treated as the truth; doc claims
are kept only as contradicted evidence. The code also has no authentication, never commits its writes,
and requires an undocumented, unused environment variable `SHELFIE_SESSION_SECRET`.

### Docs vs code

| Topic | Docs say (documented) | Code does (observed) | Evidence |
| --- | --- | --- | --- |
| Export format and path | CSV at `GET /api/v1/books/export.csv` | JSON at `GET /api/books/export` | A-E10, A-E14 vs A-E05 |
| Rating scale | 1 to 10, field `score` | 1 to 5, field `stars`, DB CHECK | A-E11, A-E14 vs A-E03, A-E04 |
| Database | PostgreSQL | SQLite (`SHELFIE_DB`, default `shelfie.db`) | A-E12 vs A-E06 |
| Architecture | three services (catalog, ratings, gateway) each with its own DB; gateway does auth | one process, one handler, one SQLite file, no auth | A-E13 vs A-E08, A-E09 |
| API prefix | `/api/v1/...` | `/api/...` (no version) | A-E14 vs A-E02, A-E04, A-E05 |
| Configuration | nothing documented | `SHELFIE_SESSION_SECRET` required at startup, never used | A-E07 |

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | sources/shelfie | 2026-11-04 | `app.py` read in full; scan clean |
| A-R02 | documentation | sources/shelfie/README.md | 2026-11-04 | out of date |
| A-R03 | documentation | sources/shelfie/docs/architecture.md | 2026-11-04 | out of date |
| A-R04 | api-spec | sources/shelfie/openapi.yaml | 2026-11-04 | out of date |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `app.py:6` | books: id, title (required), author |
| A-E02 | A-R01 | observed | `app.py:13-15` | GET /api/books lists all books as JSON |
| A-E03 | A-R01 | observed | `app.py:7-8` | ratings: book_id, stars CHECK 1-5; no key, many rows per book |
| A-E04 | A-R01 | observed | `app.py:20-27` | PUT /api/books/{id}/rating, `stars` 1-5 else 400; appends |
| A-E05 | A-R01 | observed | `app.py:16-18` | GET /api/books/export returns JSON {title, stars}, one row per rating |
| A-E06 | A-R01 | observed | `app.py:4` | SQLite, path from SHELFIE_DB |
| A-E07 | A-R01 | observed | `app.py:5` | SHELFIE_SESSION_SECRET required, unused, undocumented |
| A-E08 | A-R01 | observed | `app.py:11-34` | single process, port 8080 |
| A-E09 | A-R01 | observed | `app.py:12-27` | no auth on any route; no commit |
| A-E10 | A-R02 | documented | `README.md:3` | claims CSV export (contradicted) |
| A-E11 | A-R02 | documented | `README.md:4` | claims 1-10 ratings (contradicted) |
| A-E12 | A-R02 | documented | `README.md:5` | claims PostgreSQL (contradicted) |
| A-E13 | A-R03 | documented | `docs/architecture.md:3-4` | claims three services (contradicted) |
| A-E14 | A-R04 | documented | `openapi.yaml:3-11` | /api/v1 paths, `score` 1-10, CSV (contradicted) |
| A-E15 | A-R01 | observed | `app.py:12-23` | unknown path: no response; bad input: unhandled exception; FK not enforced |

## Features

### A-F01 Browse the library

- **Source application:** Shelfie (A)
- **Evidence:** A-E01, A-E02, A-E14
- **Description:** list every book with title and author.
- **Observed behaviour:** `GET /api/books` returns `[{id, title, author}]`. No endpoint adds, edits or deletes books.
- **Business logic:** title required, author optional; one shared library, no owner.
- **Data requirements:** Book.
- **Dependencies:** none.
- **Integration requirements:** one Book entity with an owner in a multi-user app.
- **Basis and confidence:** observed, high (only the path prefix differs from the spec).

### A-F02 Rate a book (1-5 stars)

- **Source application:** Shelfie (A)
- **Evidence:** A-E03, A-E04, A-E11, A-E14
- **Description:** give a book 1 to 5 stars.
- **Observed behaviour:** `PUT /api/books/{id}/rating` with `{"stars": n}`; 400 outside 1-5; otherwise appends a row.
- **Business logic:** 1..5 in handler and DB CHECK; appends rather than updates. Docs' 1-10 `score` is not implemented.
- **Data requirements:** Rating(book_id, stars).
- **Dependencies:** A-F01.
- **Integration requirements:** one rating per user per book in the unified app.
- **Basis and confidence:** observed, medium (docs disagree; not run).

### A-F03 Export the library (JSON)

- **Source application:** Shelfie (A)
- **Evidence:** A-E05, A-E10, A-E14
- **Description:** download titles with ratings as JSON.
- **Observed behaviour:** `GET /api/books/export` returns `[{title, stars}]` from a left join: one row per rating, or one with `stars: null`.
- **Business logic:** JSON only; no author or id. Docs' CSV export is not implemented.
- **Data requirements:** Book.title, Rating.stars.
- **Dependencies:** A-F01, A-F02.
- **Integration requirements:** export only the caller's own library.
- **Basis and confidence:** observed, medium (docs disagree; not run).

## Screens and workflows

None: Shelfie has no UI, only a JSON API.

## Navigation

None (API only).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Book | id (integer) | title (text, required), author (text) | - | observed | A-E01 |
| Rating | none | book_id (integer), stars (integer, CHECK 1-5) | book_id → Book (not enforced) | observed | A-E03 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/books` | none | - | list of {id, title, author} | unknown paths get no response | A-E02 |
| GET | `/api/books/export` | none | - | JSON list of {title, stars} | - | A-E05 |
| PUT | `/api/books/{id}/rating` | none | {stars: integer} | {ok: true} | 400 outside 1-5; unhandled exception on bad input | A-E04, A-E15 |

Documented but **not implemented**: `/api/v1/books`, `/api/v1/books/export.csv`, `PUT /api/v1/books/{id}/rating` with `score` (A-E14).

## Authentication and authorization

None observed: every route is open (A-E09). `SHELFIE_SESSION_SECRET` is required but unused (A-E07). The docs'
gateway auth (A-E13) does not exist in the code.

## Integrations

None.

## Architecture and stack

Observed: Python 3 standard library `http.server`, SQLite via `sqlite3`, one process on port 8080, no third-party
packages. Documented (contradicted): PostgreSQL and three services.

## Configuration

| Name | Purpose | Evidence |
| --- | --- | --- |
| `SHELFIE_DB` | SQLite file path, default `shelfie.db` | A-E06 |
| `SHELFIE_SESSION_SECRET` | required at startup, never used, undocumented | A-E07 |

## Error handling

Rating out of range: 400 with an error message. Unknown GET path: no response sent. Non-integer input: unhandled
exception. Rating a missing book: accepted. No commit, so writes are lost on exit (inferred from sqlite3 behaviour).

## Unknowns

- Whether any deployed copy ever matched the docs (CSV, 1-10, PostgreSQL, three services). Code treated as truth per the user.
- How books get into the library (no create endpoint).
- What `SHELFIE_SESSION_SECRET` was meant for.
- Whether a `shelfie.db` with real data exists, needed only for an import.
- Runtime behaviour not observed (running source code not approved).
