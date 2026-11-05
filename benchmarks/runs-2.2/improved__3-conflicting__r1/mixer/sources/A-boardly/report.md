# Boardly (A): reverse-engineering report

App id: A · Access: own-code · Licence: proprietary (the user's own code) · Code reuse: allowed
Slice studied: core forum loop (sign in, write a post, moderation, read posts) · Coverage: partial · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the running app, a screenshot or the code),
**documented** (official docs or a published spec), **inferred** (deduced,
not seen), or **unknown**. The structured version of this report is
`source.json` in the same folder.

## Summary

Boardly is a small pre-moderated forum. Members sign in with a cookie
session, write posts (at most 5000 characters) that start as `pending`, and
moderators publish or reject them from a moderation queue. Reading a post
requires being signed in. Everything here is **observed** in three short
files marked "illustrative"; the database layer, session middleware and
password storage are not in the folder, so coverage is partial.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | sources/boardly | 2026-11-04 | 3 files, no git, no manifest; scan: no findings |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `routes.js:4` | login stores user id in the session |
| A-E02 | A-R01 | documented | `routes.js:1` | comment: cookie sessions, every post waits for a moderator |
| A-E03 | A-R01 | observed | `routes.js:6` | create post, session required, 201, pending |
| A-E04 | A-R01 | observed | `schema.sql:2` | posts table: uuid, author not null, 5000 limit, status enum default pending |
| A-E05 | A-R01 | observed | `schema.sql:1` | users table: uuid, email unique, display_name, role member/moderator, no password column |
| A-E06 | A-R01 | observed | `routes.js:5` | read post requires session, no status check |
| A-E07 | A-R01 | observed | `routes.js:8` | moderation queue lists pending posts (moderator) |
| A-E08 | A-R01 | observed | `routes.js:9` | moderation decision sets status, value not validated in handler |
| A-E09 | A-R01 | observed | `client-routes.js:1` | screens PostList, ModerationQueue, Login |
| A-E10 | A-R01 | observed | `routes.js:2` | MAX_POST_LENGTH 5000 declared, unused in handlers |
| A-E11 | A-R01 | inferred | `routes.js:3` | no list endpoint: PostList content inferred only |

## Features

### A-F01 Sign in with a cookie session

- **Source application:** Boardly (A)
- **Evidence:** A-E01, A-E05, A-E09
- **Description:** a member signs in and gets a server-side session.
- **Observed behaviour:** POST /api/login → db.users.check(body) → req.session.userId.
- **Business logic:** roles member and moderator; credential check not visible.
- **Data requirements:** User.
- **Dependencies:** none.
- **Integration requirements:** session store, password hashing (missing from the schema).
- **Basis and confidence:** observed, medium (password storage unknown).

### A-F02 Write a post (held for moderation)

- **Source application:** Boardly (A)
- **Evidence:** A-E03, A-E04, A-E10, A-E02
- **Description:** a signed-in member writes a post that starts as pending.
- **Observed behaviour:** POST /api/posts, author = session user, 201.
- **Business logic:** author required; ≤ 5000 characters (database check); status pending.
- **Data requirements:** Post, User.
- **Dependencies:** A-F01.
- **Integration requirements:** auth.
- **Basis and confidence:** observed, high.

### A-F03 Read a post (members only)

- **Source application:** Boardly (A)
- **Evidence:** A-E06
- **Description:** a signed-in member opens a post by id.
- **Observed behaviour:** returns id, body, status for any status.
- **Business logic:** session required; no status visibility rule (any member can read pending or rejected posts by id: a weakness).
- **Data requirements:** Post.
- **Dependencies:** A-F01.
- **Integration requirements:** auth.
- **Basis and confidence:** observed, high.

### A-F04 Pre-moderation queue

- **Source application:** Boardly (A)
- **Evidence:** A-E07, A-E08, A-E04, A-E09, A-E02
- **Description:** moderators review every pending post and publish or reject it.
- **Observed behaviour:** GET /api/moderation lists pending; POST /api/moderation/:id sets status from `decision`.
- **Business logic:** moderator role only; pending → published | rejected; decision not validated in the handler.
- **Data requirements:** Post, User.
- **Dependencies:** A-F01, A-F02.
- **Integration requirements:** roles.
- **Basis and confidence:** observed, high.

### A-F05 Post list screen

- **Source application:** Boardly (A)
- **Evidence:** A-E09, A-E11
- **Description:** a /posts screen for browsing posts.
- **Observed behaviour:** the route exists; no list endpoint, so its content is not established.
- **Business logic:** unknown.
- **Data requirements:** Post.
- **Dependencies:** A-F03.
- **Integration requirements:** a list endpoint (none exists).
- **Basis and confidence:** observed (route), medium.

## Screens and workflows

| Id | Screen | Route | Components | States seen | Evidence |
| --- | --- | --- | --- | --- | --- |
| A-S01 | PostList | `/posts` | not shown | none seen | A-E09, A-E11 |
| A-S02 | ModerationQueue | `/moderation` | not shown | none seen | A-E09, A-E07 |
| A-S03 | Login | `/login` | not shown | none seen | A-E09, A-E01 |

**A-W01 Member posts, moderator publishes:** A-S03 → A-S01 → A-S02. Edge cases: rejection, over-length body, compose screen not shown.

## Navigation

Three client routes: /posts, /moderation, /login. No menu definition shown.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| User | id (uuid) | email (text, unique), display_name (text), role (member/moderator) | | observed | A-E05 |
| Post | id (uuid) | author_id (uuid, not null), body (text ≤ 5000), status (pending/published/rejected, default pending), created_at (timestamptz) | author_id → User | observed | A-E04 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/login` | none | body (credentials) | {ok} | not shown | A-E01 |
| GET | `/api/posts/:id` | session | - | {id, body, status} | not shown | A-E06 |
| POST | `/api/posts` | session | {body} | 201 post | not shown | A-E03 |
| GET | `/api/moderation` | moderator | - | pending posts | not shown | A-E07 |
| POST | `/api/moderation/:id` | moderator | {decision} | post | not shown | A-E08 |

## Authentication and authorization

Local password sign-in (inferred from login body; storage unknown), server
cookie session (observed `req.session`; cookie flags unknown), roles member
and moderator; moderation requires moderator (A-E01, A-E05, A-E07).

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| none | | | |

## Architecture and stack

Node.js handlers in an Express-style module (inferred from usage), SQL
database with uuid and timestamptz (PostgreSQL-like, inferred), client-side
router (observed). No manifest, so no versions.

## Configuration

None visible.

## Error handling

No error handling in the handlers shown; over-length bodies are refused by
the database constraint (HTTP response not shown).

## Unknowns

- Password storage and check (no password column; db layer missing).
- Failed-login behaviour.
- Session middleware, cookie flags, requireSession/requireModerator.
- What PostList lists (no list endpoint).
- Compose screen; logout.
- Database engine and package versions.
