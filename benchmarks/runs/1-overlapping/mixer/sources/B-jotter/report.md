# Jotter (B): reverse-engineering report

App id: B · Access: own-code · Licence: own code (no licence file) · Code reuse: allowed
Slice studied: core notes loop (jot, label, pin, search, export) · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented** (README), **inferred**, or
**unknown**. The structured version of this report is `source.json`.

## Summary

Jotter is a small Express API for notes held in an in-memory Map (lost on
restart). Users create, list (pinned first), edit and delete notes, append
free-text labels, pin notes, search by title only, and export every note as
`<title>.md` text. Ids are uuids. There is no auth, no validation and no
frontend in the folder; the code is labelled "illustrative". Nothing was run.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | `sources/jotter` | 2026-11-04 | 3 files, all read; scan: no findings; not run, nothing installed |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | documented | `sources/jotter/README.md:2` | jot, label, pin, export as Markdown |
| B-E02 | B-R01 | observed | `sources/jotter/package.json:1` | express ^4.18.2, uuid ^9.0.0 |
| B-E03 | B-R01 | observed | `sources/jotter/server.js:2-3` | in-memory Map, note shape |
| B-E04 | B-R01 | observed | `sources/jotter/server.js:6-9` | list pinned-first, create 201, PUT merge, DELETE 204 |
| B-E05 | B-R01 | observed | `sources/jotter/server.js:10-11` | labels appended to array |
| B-E06 | B-R01 | observed | `sources/jotter/server.js:12-13` | title-only search |
| B-E07 | B-R01 | observed | `sources/jotter/server.js:14-15` | pin endpoint |
| B-E08 | B-R01 | observed | `sources/jotter/server.js:16-17` | export JSON list of .md files (comment says zip) |

## Features

### B-F01 Note CRUD

- **Source application:** Jotter (B)
- **Evidence:** B-E03, B-E04
- **Description:** create, list, edit, delete notes (title, content)
- **Observed behaviour:** list sorted pinned first; create returns 201 with uuid; PUT merges the whole request body; DELETE 204
- **Business logic:** no validation; PUT can overwrite id/pinned; updatedAt never refreshed; in-memory only
- **Data requirements:** Note
- **Dependencies:** none
- **Basis and confidence:** observed, high

### B-F02 Labels

- **Source application:** Jotter (B)
- **Evidence:** B-E05, B-E01
- **Description:** add free-text labels to a note
- **Observed behaviour:** label string pushed onto `labels`
- **Business logic:** no de-duplication, no shared label list
- **Data requirements:** Note.labels
- **Dependencies:** B-F01
- **Basis and confidence:** observed, high

### B-F03 Search titles

- **Source application:** Jotter (B)
- **Evidence:** B-E06
- **Description:** title-only search
- **Observed behaviour:** `title.includes(q)`, case-sensitive
- **Business logic:** body/content not searched
- **Data requirements:** Note
- **Dependencies:** B-F01
- **Basis and confidence:** observed, high

### B-F04 Pin notes

- **Source application:** Jotter (B)
- **Evidence:** B-E07, B-E04, B-E01
- **Description:** pin important notes to the top
- **Observed behaviour:** pin sets `pinned = true`; list sorts pinned first
- **Business logic:** no unpin endpoint (only via PUT, inferred)
- **Data requirements:** Note.pinned
- **Dependencies:** B-F01
- **Basis and confidence:** observed, high

### B-F05 Export as Markdown

- **Source application:** Jotter (B)
- **Evidence:** B-E08, B-E01
- **Description:** export every note as a Markdown file
- **Observed behaviour:** JSON list of `{file: "<title>.md", text}`
- **Business logic:** raw title as file name; comment promises a zip that the code does not build
- **Data requirements:** Note
- **Dependencies:** B-F01
- **Basis and confidence:** observed, medium (comment and code disagree)

## Screens and workflows

No screens are in the source folder.

## Navigation

Unknown (no frontend). HTTP routes are listed under API.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Note | id (uuid) | title (string), content (string), labels (string[]), pinned (boolean), updatedAt (Date) | none | observed | B-E03 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/notes` | none | - | notes, pinned first | - | B-E04 |
| POST | `/api/notes` | none | title, content | 201 note | - | B-E04 |
| PUT | `/api/notes/:id` | none | any fields | note | 500 on unknown id (inferred) | B-E04 |
| DELETE | `/api/notes/:id` | none | - | 204 | - | B-E04 |
| POST | `/api/notes/:id/labels` | none | label | note | 500 on unknown id (inferred) | B-E05 |
| GET | `/api/search` | none | q | notes | - | B-E06 |
| POST | `/api/notes/:id/pin` | none | - | note | 500 on unknown id (inferred) | B-E07 |
| GET | `/api/export` | none | - | list of {file, text} | - | B-E08 |

## Authentication and authorization

None observed (B-E04).

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| (none) | | | |

## Architecture and stack

Node.js + Express ^4.18.2, uuid ^9.0.0 (observed, B-E02); no database.

## Configuration

None found.

## Error handling

Unknown ids make handlers throw (inferred); missing `q` searches for the
string "undefined" (inferred).

## Unknowns

- App bootstrap (body parser, port) is outside the folder.
- No frontend; screens unknown.
- Export: zip (comment) or JSON list (code)? Ask the user.
- Code not run (not approved); behaviour read from code only.
