# Passbook (A): reverse-engineering report

App id: A · Access: own-code · Licence: proprietary (user's own code) · Code reuse: allowed
Slice studied: email and password accounts · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented**, **inferred**, or **unknown**.
The structured version of this report is `source.json` in the same folder.

## Summary

Passbook provides email and password accounts in one 12-line Python module
(`accounts.py`). Registration stores a salted PBKDF2-HMAC-SHA256 hash and the
role `user`; login returns a random session token. Important findings: an
existing email is silently overwritten on re-registration (account takeover),
the hash comparison is not constant time, and sessions never expire and
cannot be revoked (no logout). All observed.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | `sources/passbook` | 2026-11-05 | 1 file; scanned first (no findings); read only, nothing run |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `sources/passbook/accounts.py:4-7` | Register: lowercased email, 16-byte salt, PBKDF2-SHA256 100k, role `user`, id len+1 |
| A-E02 | A-R01 | observed | `sources/passbook/accounts.py:6` | No duplicate check: re-registering replaces the account |
| A-E03 | A-R01 | observed | `sources/passbook/accounts.py:8-12` | Login: same ValueError for unknown email and wrong password; `!=` comparison; token_urlsafe(24) in SESSIONS |
| A-E04 | A-R01 | observed | `sources/passbook/accounts.py:2-3` | In-memory USERS and SESSIONS; no logout, lookup or expiry |

## Features

### A-F01 Email and password registration

- **Source application:** Passbook (A)
- **Evidence:** A-E01, A-E02
- **Description:** create an account from an email and a password.
- **Observed behaviour:** email lowercased, salted PBKDF2 hash stored, role `user`, sequential integer id.
- **Business logic:** email case-insensitive; no password rules; duplicate email overwrites the old account.
- **Data requirements:** User (id, email, salt, hash, role).
- **Dependencies:** none.
- **Integration requirements:** unified user store, unified role set.
- **Basis and confidence:** observed, high

### A-F02 Password login with session token

- **Source application:** Passbook (A)
- **Evidence:** A-E03, A-E04
- **Description:** sign in with email and password, get a session token.
- **Observed behaviour:** recompute hash; ValueError("bad credentials") on any failure; random token stored against the user id.
- **Business logic:** one error for both failure cases; tokens never expire; no logout.
- **Data requirements:** User, Session (token, user_id).
- **Dependencies:** A-F01.
- **Integration requirements:** unified sessions, whoami, logout.
- **Basis and confidence:** observed, high

## Screens and workflows

No screens: the slice is a library module. (observed)

## Navigation

None in the slice.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| User | id (integer) | email (text), salt (bytes), hash (bytes), role (text) | - | observed | A-E01, A-E04 |
| Session | token (text) | user_id (integer) | user_id -> User | observed | A-E03, A-E04 |

## API

Python functions, no HTTP: `register(email, password)`, `login(email, password) -> token`. (observed)

## Authentication and authorization

Local password provider; PBKDF2-HMAC-SHA256 with 100,000 iterations; opaque
token sessions in memory without expiry; one role string `user`, never
checked. (observed, A-E01, A-E03)

## Integrations

None.

## Architecture and stack

Python standard library only (hashlib, os, secrets); module-level dicts as
storage. (observed)

## Configuration

None.

## Error handling

Unknown email and wrong password both raise `ValueError("bad credentials")`;
duplicate registration raises nothing. (observed)

## Unknowns

- Only `accounts.py` was provided; whether Passbook has password reset, email verification or logout elsewhere is unknown.
