# OpenForum (B): reverse-engineering report

App id: B · Access: open-source · Licence: MIT (LICENSE checked) · Code reuse: allowed (keep the notice)
Slice studied: sign in, post (including anonymous), read posts · Coverage: complete (all 3 files read) · Size: S

Every statement is from reading the code (**observed**) unless marked otherwise. Nothing was run. Structured version: `source.json`.

## Summary

OpenForum is an open, unmoderated forum. Users sign in for a JWT bearer token; posts of up to 10000 characters publish immediately, and posting without a token creates an anonymous post (null author). Data uses integer keys and has no post status. The JWT signing key is a hard-coded literal in the code (security weakness; value not copied here). An `admin` role exists but nothing uses it.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | sources/openforum | 2026-11-04 | 3 files, scanned (no findings), indexed, read; not run |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `sources/openforum/api.py:1` | JWT; immediate publish; anonymous posting |
| B-E02 | B-R01 | observed | `sources/openforum/api.py:4` | login returns JWT signed with a hard-coded key |
| B-E03 | B-R01 | observed | `sources/openforum/api.py:8` | GET post by int id, public |
| B-E04 | B-R01 | observed | `sources/openforum/api.py:11` | POST post; no token = anonymous |
| B-E05 | B-R01 | observed | `sources/openforum/api.py:12` | 10000-char limit |
| B-E06 | B-R01 | observed | `sources/openforum/api.py:17` | route map |
| B-E07 | B-R01 | observed | `sources/openforum/api.py:18` | client routes /posts, /login |
| B-E08 | B-R01 | observed | `sources/openforum/models.py:2` | users: int id, name, role user/admin |
| B-E09 | B-R01 | observed | `sources/openforum/models.py:3` | posts: int id, nullable author, no status |
| B-E10 | B-R01 | observed | `sources/openforum/models.py:4` | MAX_POST_LENGTH, ROLES |
| B-E11 | B-R01 | observed | `sources/openforum/LICENSE:1` | MIT licence |

## Features

### B-F01 Token sign-in (JWT bearer)
- **Evidence:** B-E01, B-E02, B-E06 · POST /api/token returns a JWT with sub and role; hard-coded key, no expiry seen. · observed, high

### B-F02 Read a post (public)
- **Evidence:** B-E03, B-E06 · no auth needed. · observed, high

### B-F03 Create a post (published immediately)
- **Evidence:** B-E01, B-E04, B-E05, B-E09, B-E10 · max 10000 chars, no review. · observed, high

### B-F04 Anonymous posting
- **Evidence:** B-E01, B-E04, B-E09 · no token → author_id null, published at once. · observed, high

### B-F05 Post list screen
- **Evidence:** B-E07 · /posts route; no list endpoint. · observed, low

## Screens and workflows

| Id | Screen | Route | Components | States seen | Evidence |
| --- | --- | --- | --- | --- | --- |
| B-S01 | Posts | `/posts` | unknown | none seen | B-E07 |
| B-S02 | Login | `/login` | unknown | none seen | B-E07 |

**B-W01 Post anonymously:** B-S01. **B-W02 Sign in and post:** B-S02 → B-S01.

## Navigation

Two client routes.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| User | id (integer) | email, name, role (user/admin) | - | observed | B-E08 |
| Post | id (integer) | author_id (integer, nullable), body (<= 10000), created_at (timestamp) | author_id → User | observed | B-E09 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/token` | none | email, password | {token} | unknown | B-E02 |
| GET | `/api/posts/<int:post_id>` | none | - | {id, body, author_id} | unknown | B-E03 |
| POST | `/api/posts` | optional bearer | {body} | post | ValueError too long | B-E04, B-E05 |

## Authentication and authorization

Own users table; stateless JWT bearer; roles user/admin in token; no authorization checks seen.

## Integrations

PyJWT library only.

## Architecture and stack

Python functions mapped in a ROUTES dict; framework unknown; PyJWT imported.

## Configuration

JWT signing key should be configuration; currently hard-coded (value not copied).

## Error handling

ValueError on long body; token decode errors unhandled in the shown code.

## Unknowns

- Framework, HTTP error mapping, db helper, password hashing.
- Purpose of the admin role.
- No list endpoint behind /posts.
- Nothing was run.
