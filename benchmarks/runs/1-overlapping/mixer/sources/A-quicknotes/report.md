# QuickNotes (A): reverse-engineering report

App id: A · Access: own-code · Licence: own code (no licence file) · Code reuse: allowed
Slice studied: core notes loop (write, tag, search, preview) · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented** (README), **inferred**, or
**unknown**. The structured version of this report is `source.json`.

## Summary

QuickNotes is a small backend for Markdown notes. Users create, list, edit and
delete notes (newest first), attach shared tags, search title and body by
substring, and preview the Markdown body as HTML. Data lives in a relational
schema (notes, tags, note_tags with cascading deletes). There is no auth and
no frontend in the folder; the handlers are labelled "illustrative" and call a
`db` helper that is not included. Nothing was run.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | `sources/quicknotes` | 2026-11-04 | 3 files, all read; scan: no findings; not run |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | documented | `sources/quicknotes/README.md:2` | Markdown notes, tags, search all text |
| A-E02 | A-R01 | observed | `sources/quicknotes/schema.sql:1` | notes table and NOT NULL columns |
| A-E03 | A-R01 | observed | `sources/quicknotes/app.py:4-7` | list/create/update/delete handlers |
| A-E04 | A-R01 | observed | `sources/quicknotes/schema.sql:2-3` | tags (unique name), note_tags with cascades |
| A-E05 | A-R01 | observed | `sources/quicknotes/app.py:9-11` | tag_note get-or-create |
| A-E06 | A-R01 | observed | `sources/quicknotes/app.py:13-15` | LIKE search on title or body |
| A-E07 | A-R01 | observed | `sources/quicknotes/app.py:17-19` | Markdown render for preview |
| A-E08 | A-R01 | observed | `sources/quicknotes/app.py:21-23` | route table |
| A-E09 | A-R01 | observed | `sources/quicknotes/app.py:1-2` | illustrative Flask-style; markdown import |

## Features

### A-F01 Note CRUD

- **Source application:** QuickNotes (A)
- **Evidence:** A-E02, A-E03, A-E08
- **Description:** create, list, edit, delete notes with title and Markdown body
- **Observed behaviour:** list ordered by created_at desc; create/update set title and body; delete removes the row
- **Business logic:** title and body NOT NULL; cascade to note_tags
- **Data requirements:** Note
- **Dependencies:** none
- **Integration requirements:** persistent relational storage
- **Basis and confidence:** observed, high

### A-F02 Tags

- **Source application:** QuickNotes (A)
- **Evidence:** A-E04, A-E05, A-E08, A-E01
- **Description:** attach shared, uniquely named tags to notes
- **Observed behaviour:** get-or-create tag by name, insert link row
- **Business logic:** unique tag name; many-to-many; no unique constraint on the link pair
- **Data requirements:** Tag, NoteTag
- **Dependencies:** A-F01
- **Basis and confidence:** observed, high

### A-F03 Search title and body

- **Source application:** QuickNotes (A)
- **Evidence:** A-E06, A-E08, A-E01
- **Description:** substring search over title and body
- **Observed behaviour:** `LIKE %text%` on title OR body (comment calls it full-text; it is not an FTS index)
- **Business logic:** case sensitivity depends on the database (inferred)
- **Data requirements:** Note
- **Dependencies:** A-F01
- **Basis and confidence:** observed, high

### A-F04 Markdown preview

- **Source application:** QuickNotes (A)
- **Evidence:** A-E07, A-E08, A-E01
- **Description:** render the body to HTML for a preview pane
- **Observed behaviour:** `GET /notes/<id>/preview` returns rendered HTML
- **Business logic:** no sanitisation visible
- **Data requirements:** Note
- **Dependencies:** A-F01
- **Integration requirements:** Markdown renderer plus HTML sanitiser
- **Basis and confidence:** observed, high

## Screens and workflows

No screens are in the source folder. A preview pane is mentioned in a code
comment only (A-E07); its layout is unknown.

## Navigation

Unknown (no frontend). HTTP routes are listed under API.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Note | id (integer autoincrement) | title (text, req), body (text, req), created_at (timestamp, req) | many-to-many Tag via NoteTag | observed | A-E02 |
| Tag | id (integer autoincrement) | name (text, unique) | | observed | A-E04 |
| NoteTag | none | note_id, tag_id | → Note, → Tag (cascade) | observed | A-E04 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/notes` | none | - | notes, newest first | unknown | A-E03 |
| POST | `/notes` | none | title, body | note | unknown | A-E03 |
| PUT | `/notes/<id>` | none | title, body | note | unknown | A-E03 |
| DELETE | `/notes/<id>` | none | - | - | unknown | A-E03 |
| POST | `/notes/<id>/tags` | none | tag name | - | unknown | A-E05 |
| GET | `/search` | none | text | notes | unknown | A-E06 |
| GET | `/notes/<id>/preview` | none | - | HTML | unknown | A-E07 |

## Authentication and authorization

None observed (A-E08): no login, sessions, roles or ownership checks.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| (none) | | | |

## Architecture and stack

Python, Flask-style handlers (observed, labelled illustrative, A-E09);
relational DB, SQLite likely from `autoincrement` (inferred); `markdown`
package, version unknown (no manifest).

## Configuration

None found.

## Error handling

Not handled in the handlers; missing-id behaviour depends on the absent
`db` helper (unknown). Empty strings pass NOT NULL (inferred).

## Unknowns

- The `db` helper is not in the folder: how created_at is set and missing ids handled.
- No frontend: preview pane and editor screens unknown.
- markdown package name/version and sanitisation unknown (no manifest).
- Code not run (not approved); behaviour read from code only.
