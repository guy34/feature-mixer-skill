# Linkup (B): reverse-engineering report

App id: B · Access: open-source · Licence: MIT per the user; no licence file present · Code reuse: not-allowed
Slice studied: OAuth provider sign-in · Coverage: complete · Size: S

Every statement is **observed** in the code unless marked otherwise. Structured copy: `source.json`.

## Summary

Linkup is one Python module (`oauth.py`, 7 lines) handling the callback of a Google-style OAuth sign-in. Accounts are
keyed by `(provider, subject)`; the first sign-in creates an account with id `lu-<n>`, the provider's email as given,
and role `member`. The provider's `email_verified` flag is received but ignored, there is no account linking, and no
session is issued. The redirect, code exchange and token signature checks are not in the source.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | sources/linkup | 2026-11-04 | 1 file, scanned first: no findings; no LICENSE file |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `sources/linkup/oauth.py:1-2` | accounts keyed by (provider, subject); id, email, role `member` |
| B-E02 | B-R01 | observed | `sources/linkup/oauth.py:3-7` | callback creates on first sight, returns the account; email_verified unused |

## Features

### B-F01 Sign in with an OAuth provider

- **Source application:** Linkup (B)
- **Evidence:** B-E01, B-E02
- **Description:** sign in through a provider; the first sign-in creates the account.
- **Observed behaviour:** lookup by (provider, subject); create with id `lu-<n>`, email, role `member`; return the record.
- **Business logic:** identity is (provider, subject); email not normalised; email_verified ignored; no linking.
- **Data requirements:** Account (id, provider, subject, email, role).
- **Dependencies:** none.
- **Integration requirements:** unified user store, linking rule, session, a provider adapter.
- **Basis and confidence:** observed, high

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Account | id (string `lu-<n>`) | provider (string), subject (string), email (string), role (string: member) | - | observed | B-E01, B-E02 |

## API

No HTTP API: `callback(provider, subject, email, email_verified) -> account`.

## Authentication and authorization

External OAuth provider; no session in the source; one role, `member`, never checked.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| Google-style OAuth provider | supplies subject, email, email_verified | B-F01 | B-E01 |

## Architecture and stack

Python 3, no imports, in-memory dict (observed).

## Configuration

None in the source (a real provider would need a client id and secret; names only, none present).

## Error handling

None: every call succeeds and repeat sign-ins return the existing account.

## Unknowns

- Redirect, code exchange and ID-token verification are not in the source; a real provider cannot be tested here.
- What `member` may do: no permission checks exist.
- Licence: the user says MIT, but no licence file is in `sources/linkup`; code reuse recorded as not-allowed.
