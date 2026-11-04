# ShareLink (C): reverse-engineering report

App id: C · Access: own-code · Licence: proprietary (user's own code) · Code reuse: allowed
Slice studied: create, open and revoke share links · Coverage: complete · Size: S

Basis is **observed** (read in the code). Structured version: `source.json`.

## Summary

ShareLink creates unguessable tokens that point at a file id, expire after a number of hours (default 24)
and can require a password. Opening a link checks expiry and password and returns the file id; revoking
removes it. Links live in a caller-supplied dict. Passwords are hashed with unsalted SHA-256 and there is
no ownership check on create or revoke.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| C-R01 | local-directory | sources/sharelink | 2026-11-04 | 1 file, read in full; scan: no findings |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| C-E01 | C-R01 | observed | `sources/sharelink/sharelink.py:4-8` | token + expiry creation |
| C-E02 | C-R01 | observed | `sources/sharelink/sharelink.py:7` | unsalted SHA-256 password hash |
| C-E03 | C-R01 | observed | `sources/sharelink/sharelink.py:10-16` | open: expiry, password, returns file_id |
| C-E04 | C-R01 | observed | `sources/sharelink/sharelink.py:18-19` | revoke without ownership check |
| C-E05 | C-R01 | observed | `sources/sharelink/sharelink.py:2` | standard library imports only |

## Features

### C-F01 Create share link with expiry

- **Source application:** ShareLink (C) · **Evidence:** C-E01
- **Behaviour:** token_urlsafe(16); expires after expires_in_hours (default 24). **Basis and confidence:** observed, high

### C-F02 Password-protected link

- **Source application:** ShareLink (C) · **Evidence:** C-E02, C-E03
- **Behaviour:** optional password, unsalted SHA-256. **Basis and confidence:** observed, high

### C-F03 Open shared link

- **Source application:** ShareLink (C) · **Evidence:** C-E03
- **Behaviour:** unknown/expired → LookupError; wrong password → PermissionError; else file_id. **Basis and confidence:** observed, high

### C-F04 Revoke share link

- **Source application:** ShareLink (C) · **Evidence:** C-E04
- **Behaviour:** removes token; silent if missing; no owner check. **Basis and confidence:** observed, high

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| ShareLink | token (str) | file_id (str), expires_at (float), password_hash (str or None) | file_id → File | observed | C-E01, C-E02 |

## API

No endpoints; functions `create_link`, `open_link`, `revoke_link`.

## Authentication and authorization

Link-level only (optional password); no user identity.

## Architecture and stack

Plain Python functions, standard library (hashlib, secrets, time).

## Error handling

LookupError for unknown/expired, PermissionError for wrong password, silent revoke of unknown token.

## Unknowns

- Persistence of links (dict only).
- Who may create or revoke links (no owner concept).
