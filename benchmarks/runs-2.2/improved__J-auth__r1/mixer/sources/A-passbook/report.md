# Passbook (A): reverse-engineering report

App id: A · Access: own-code · Licence: proprietary (the user's own code) · Code reuse: allowed
Slice studied: email and password accounts · Coverage: complete · Size: S

Every statement is **observed** in the code unless marked otherwise. Structured copy: `source.json`.

## Summary

Passbook is a single Python module (`accounts.py`, 12 lines) that keeps email-and-password accounts in memory.
Registration lowercases the email, salts and hashes the password with PBKDF2-HMAC-SHA256 (100,000 iterations)
and gives every account the role `user`. Login returns a random session token. Important findings: re-registering
an existing email silently overwrites the account (takeover), the hash comparison is not constant-time, and sessions
have no logout, lookup or expiry.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | sources/passbook | 2026-11-04 | 1 file, scanned first: no findings |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `sources/passbook/accounts.py:2` | USERS keyed by email: id, salt, hash, role `user` |
| A-E02 | A-R01 | observed | `sources/passbook/accounts.py:4-7` | register: lowercase, 16-byte salt, PBKDF2-SHA256 100k, id len+1, overwrites existing email |
| A-E03 | A-R01 | observed | `sources/passbook/accounts.py:8-11` | login: same ValueError for unknown email and wrong password; `!=` compare |
| A-E04 | A-R01 | observed | `sources/passbook/accounts.py:12` | token_urlsafe(24) stored in SESSIONS; no logout or expiry |

## Features

### A-F01 Register with email and password

- **Source application:** Passbook (A)
- **Evidence:** A-E01, A-E02
- **Description:** create an account from email and password.
- **Observed behaviour:** email lowercased, password hashed with a random salt, role `user`, integer id.
- **Business logic:** email case-insensitive; no password rules; an existing email is overwritten (flaw).
- **Data requirements:** User (id, email, salt, hash, role).
- **Dependencies:** none.
- **Integration requirements:** unified user store, role model.
- **Basis and confidence:** observed, high

### A-F02 Log in with email and password

- **Source application:** Passbook (A)
- **Evidence:** A-E03, A-E04
- **Description:** sign in and receive a session token.
- **Observed behaviour:** re-hash with stored salt; match returns a new token recorded in SESSIONS; else ValueError.
- **Business logic:** one error message for both failure causes; non-constant-time compare; no expiry, no logout.
- **Data requirements:** User, Session (token, user_id).
- **Dependencies:** A-F01.
- **Integration requirements:** unified session store with logout and lookup.
- **Basis and confidence:** observed, high

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| User | id (integer) | email (string, lowercased, unique), salt (bytes), hash (bytes), role (string: user) | - | observed | A-E01, A-E02 |
| Session | token (string) | user_id (integer) | user_id → User | observed | A-E04 |

## API

No HTTP API: two Python functions, `register(email, password)` and `login(email, password) -> token`.

## Authentication and authorization

Own local accounts, password sign-in, opaque bearer token in memory with no expiry. One role, `user`, which nothing
checks (A-E01).

## Integrations

None.

## Architecture and stack

Python 3 standard library (`hashlib`, `os`, `secrets`); in-memory dicts (observed).

## Configuration

None.

## Error handling

`ValueError("bad credentials")` for any login failure. Duplicate registration is not an error (overwrites).

## Unknowns

- What the `user` role may do: no permission checks exist.
- Whether overwriting on re-registration is intended; treated as a flaw.
