# Linkup (B): reverse-engineering report

App id: B · Access: open-source · Licence: MIT stated by the user, no licence file present · Code reuse: not-allowed
Slice studied: sign-in with an OAuth provider · Coverage: partial · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented**, **inferred**, or **unknown**.
The structured version of this report is `source.json` in the same folder.

## Summary

Linkup's provided code is the OAuth callback (`oauth.py`, 7 lines). Accounts
are keyed by (provider, subject); the first sign-in creates an account with
the provider's email and role `member`. The provider's `email_verified` flag
is received but ignored, and no session or token is issued by the callback.
The OAuth exchange itself is not in the provided code, so coverage is partial.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | `sources/linkup` | 2026-11-05 | 1 file; scanned first (no findings); no LICENSE file |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `sources/linkup/oauth.py:1-2` | Accounts keyed by (provider, subject); provider sends email and email_verified |
| B-E02 | B-R01 | observed | `sources/linkup/oauth.py:3-7` | Find-or-create on first sign-in; id `lu-<n>`; role `member`; email_verified unused |
| B-E03 | B-R01 | observed | `sources/linkup/oauth.py:3-7` | Returns the account, issues no token; email never updated |

## Features

### B-F01 Sign in with an OAuth provider

- **Source application:** Linkup (B)
- **Evidence:** B-E01, B-E02, B-E03
- **Description:** sign in through an external provider; account created on first sign-in.
- **Observed behaviour:** callback(provider, subject, email, email_verified) finds or creates the (provider, subject) account and returns it.
- **Business logic:** identity key (provider, subject); default role `member`; `email_verified` ignored; no linking to other accounts.
- **Data requirements:** Account (id, email, role, provider, subject).
- **Dependencies:** none.
- **Integration requirements:** unified user store, an account-linking rule, unified sessions.
- **Basis and confidence:** observed, high

## Screens and workflows

No screens in the provided code. (observed)

## Navigation

None in the slice.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Account | id (text, `lu-<n>`) | email (text), role (text), provider (text), subject (text) | - | observed | B-E01, B-E02 |

## API

Python function `callback(provider, subject, email, email_verified) -> account`. (observed)

## Authentication and authorization

External OAuth provider (Google-style); sign-in method `oauth`; session
mechanism unknown; one role `member`, never checked. (observed, B-E01, B-E02)

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| OAuth identity provider | federated sign-in | B-F01 | B-E01 |

## Architecture and stack

Python with no imports; module-level dict as storage. (observed)

## Configuration

None in the provided code (client id and secret names unknown).

## Error handling

callback() validates nothing and raises nothing. (observed)

## Unknowns

- The OAuth flow before the callback (redirect, state/nonce, code exchange, ID-token signature and audience checks) is not in the provided code.
- Linkup's session mechanism after sign-in is unknown.
- No LICENSE file in `sources/linkup`; code reuse is not-allowed until one is provided (the task says MIT).
