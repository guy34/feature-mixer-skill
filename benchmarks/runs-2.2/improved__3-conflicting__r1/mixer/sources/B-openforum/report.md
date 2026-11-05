# OpenForum (B): reverse-engineering report

App id: B · Access: open-source · Licence: MIT · Code reuse: allowed
Slice studied: core forum loop (sign in, write a post, read posts) · Coverage: partial · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the running app, a screenshot or the code),
**documented** (official docs or a published spec), **inferred** (deduced,
not seen), or **unknown**. The structured version of this report is
`source.json` in the same folder.

## Summary

OpenForum is an open forum: posts go live the moment they are written,
anyone can post without an account (the post then has no author), and
anyone can read a post without signing in. Signed-in users get a JWT bearer
token. Its models are given as SQL in comments (**documented**), its
handlers are **observed**. The scan found the JWT signing key hard-coded in
`api.py` (two medium findings; the value was not copied anywhere). The web
framework and db layer are not in the folder, so coverage is partial.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | sources/openforum | 2026-11-04 | 3 files incl. MIT LICENSE; scan: 2 medium weak-secret findings |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `api.py:4` | login returns JWT (sub, role) signed with a literal key |
| B-E02 | B-R01 | documented | `api.py:1` | comment: JWT bearer, instant publish, anonymous posting |
| B-E03 | B-R01 | observed | `api.py:11` | create post: >10000 refused, author from token or None, no status |
| B-E04 | B-R01 | observed | `api.py:8` | read post by int id, no auth |
| B-E05 | B-R01 | observed | `api.py:17` | route table |
| B-E06 | B-R01 | observed | `api.py:18` | client routes /posts, /login |
| B-E07 | B-R01 | documented | `models.py:2` | users: int id, email, name, role user/admin |
| B-E08 | B-R01 | documented | `models.py:3` | posts: int id, nullable author, body ≤ 10000, created_at timestamp, no status |
| B-E09 | B-R01 | observed | `models.py:4` | MAX_POST_LENGTH 10000, ROLES user/admin |
| B-E10 | B-R01 | observed | `LICENSE:1` | MIT |
| B-E11 | B-R01 | inferred | `api.py:17` | no list endpoint: /posts content inferred only |
| B-E12 | B-R01 | observed | `api.py:14` | jwt.decode with literal key, no algorithms argument |

## Features

### B-F01 Sign in with a bearer token (JWT)

- **Source application:** OpenForum (B)
- **Evidence:** B-E01, B-E05, B-E12, B-E02
- **Description:** email and password exchanged for a signed JWT.
- **Observed behaviour:** POST /api/token → {token} with sub and role.
- **Business logic:** literal signing key, no expiry, decode without an algorithms list.
- **Data requirements:** User.
- **Dependencies:** none.
- **Integration requirements:** a secret store (missing), token verification.
- **Basis and confidence:** observed, medium (insecure as written; library version unknown).

### B-F02 Write a post (up to 10000 characters)

- **Source application:** OpenForum (B)
- **Evidence:** B-E03, B-E05, B-E09, B-E08
- **Description:** create a post of at most 10000 characters.
- **Observed behaviour:** inserts the post; longer bodies raise ValueError.
- **Business logic:** max 10000.
- **Data requirements:** Post.
- **Dependencies:** none.
- **Integration requirements:** none.
- **Basis and confidence:** observed, high.

### B-F03 Instant publishing

- **Source application:** OpenForum (B)
- **Evidence:** B-E03, B-E04, B-E08, B-E02
- **Description:** posts are visible at once; no review.
- **Observed behaviour:** no status on insert; read returns any post.
- **Business logic:** no moderation.
- **Data requirements:** Post.
- **Dependencies:** B-F02.
- **Integration requirements:** none.
- **Basis and confidence:** observed, high.

### B-F04 Anonymous posting

- **Source application:** OpenForum (B)
- **Evidence:** B-E03, B-E08, B-E02
- **Description:** post without an account; no author recorded.
- **Observed behaviour:** no token → author_id None, post inserted.
- **Business logic:** author optional.
- **Data requirements:** Post.
- **Dependencies:** B-F02.
- **Integration requirements:** abuse protection (none present).
- **Basis and confidence:** observed, high.

### B-F05 Read a post (public)

- **Source application:** OpenForum (B)
- **Evidence:** B-E04, B-E05
- **Description:** anyone opens a post by id.
- **Observed behaviour:** no auth; returns id, body, author_id.
- **Business logic:** none.
- **Data requirements:** Post.
- **Dependencies:** none.
- **Integration requirements:** none.
- **Basis and confidence:** observed, high.

### B-F06 Post list screen

- **Source application:** OpenForum (B)
- **Evidence:** B-E06, B-E11
- **Description:** a /posts screen for browsing.
- **Observed behaviour:** route exists; no list endpoint.
- **Business logic:** unknown.
- **Data requirements:** Post.
- **Dependencies:** B-F05.
- **Integration requirements:** a list endpoint (none exists).
- **Basis and confidence:** observed (route), medium.

## Screens and workflows

| Id | Screen | Route | Components | States seen | Evidence |
| --- | --- | --- | --- | --- | --- |
| B-S01 | Posts | `/posts` | not shown | none seen | B-E06, B-E11 |
| B-S02 | Login | `/login` | not shown | none seen | B-E06, B-E01 |

**B-W01 Post straight to the forum:** B-S02 → B-S01. Edge cases: no token (anonymous), over-length body.

## Navigation

Two client routes: /posts and /login.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| User | id (integer) | email (text), name (text), role (user/admin) | | documented | B-E07, B-E09 |
| Post | id (integer) | author_id (integer, null = anonymous), body (text ≤ 10000), created_at (timestamp) | author_id → User | documented | B-E08, B-E03 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/token` | none | email, password | {token} | not shown | B-E01 |
| GET | `/api/posts/<int:post_id>` | none | - | {id, body, author_id} | not shown | B-E04 |
| POST | `/api/posts` | optional bearer | {body} | post | ValueError on > 10000 | B-E03 |

## Authentication and authorization

Local password sign-in; JWT bearer token with sub and role; signing key is
a hard-coded literal (scan, medium); no expiry; verification passes no
algorithms list. Roles user and admin exist, but no code checks either
(B-E01, B-E09, B-E12).

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| none | | | |

## Architecture and stack

Python, PyJWT (version undeclared), web framework and database not shown
(inferred).

## Configuration

The JWT signing key is hard-coded, not configured (value not copied).

## Error handling

Over-length body raises ValueError; bad tokens raise in jwt.decode; how
either reaches the client is not shown.

## Unknowns

- Password storage and db.check.
- Web framework and error mapping.
- PyJWT version and so whether decode without algorithms works or accepts any algorithm.
- Admin role's powers.
- Token expiry.
- What /posts lists.
- Real schema constraints (models are comments).
