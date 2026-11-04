# Uploader (A): reverse-engineering report

App id: A · Access: own-code · Licence: proprietary (user's own code) · Code reuse: allowed
Slice studied: upload, list and delete own files · Coverage: complete · Size: S

Basis is **observed** (read in the code) unless marked otherwise. Structured version: `source.json`.

## Summary

Uploader is a small Python module that stores files for an owner, lists an owner's files and deletes them.
Uploads above 10 MB are rejected. Persistence goes through a `store` object that is not part of the source,
and there is no HTTP layer or authentication. The data model is one `files` table.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | sources/uploader | 2026-11-04 | 2 files, read in full; scan: no findings |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `sources/uploader/uploader.py:2` | 10 MB upload limit |
| A-E02 | A-R01 | observed | `sources/uploader/uploader.py:4-7` | upload rejects > 10 MB, else store.save |
| A-E03 | A-R01 | observed | `sources/uploader/uploader.py:9-10` | list scoped by owner |
| A-E04 | A-R01 | observed | `sources/uploader/uploader.py:12-13` | delete scoped by owner |
| A-E05 | A-R01 | observed | `sources/uploader/schema.sql:1` | files table |
| A-E06 | A-R01 | inferred | `sources/uploader/uploader.py:1` | store not included; module is illustrative |

## Features

### A-F01 Upload a file

- **Source application:** Uploader (A)
- **Evidence:** A-E01, A-E02, A-E05
- **Description:** owner uploads a named file.
- **Observed behaviour:** > 10 MB raises "file too large"; otherwise saved with name and size.
- **Business logic:** limit 10 * 1024 * 1024 bytes, inclusive.
- **Data requirements:** File(owner_id, name, size, created_at).
- **Dependencies:** none.
- **Integration requirements:** owner identity (auth) and byte storage.
- **Basis and confidence:** observed, high

### A-F02 List my files

- **Source application:** Uploader (A) · **Evidence:** A-E03, A-E05
- **Description / behaviour:** returns the owner's files only.
- **Dependencies:** A-F01 · **Basis and confidence:** observed, high

### A-F03 Delete my file

- **Source application:** Uploader (A) · **Evidence:** A-E04
- **Description / behaviour:** deletes by owner and file id; missing-file behaviour depends on the absent store.
- **Dependencies:** A-F01 · **Basis and confidence:** observed, medium

## Screens and workflows

None in the source (no UI or HTTP layer).

## Navigation

None.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| File | id (text) | owner_id (text), name (text), size (integer), created_at (timestamp) | owner_id → owner (no user table) | observed | A-E05 |

## API

No endpoints; Python functions `upload`, `list_files`, `delete_file`.

## Authentication and authorization

None in the source; owner_id is supplied by the caller (unknown how it is authenticated).

## Integrations

None.

## Architecture and stack

Python functions over an injected store; SQL schema (dialect not stated).

## Configuration

`MAX_BYTES` constant only.

## Error handling

Over-size upload raises ValueError("file too large").

## Unknowns

- Store implementation: id generation, byte storage (no data column), delete of missing/foreign file.
- Authentication: how owner_id is established.
- No routes or screens exist.
