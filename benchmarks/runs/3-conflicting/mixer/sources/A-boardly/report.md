# Boardly (A): reverse-engineering report

App id: A · Access: own-code · Licence: proprietary (user's own) · Code reuse: allowed
Slice studied: sign in, post, read posts, moderation queue · Coverage: complete (all 3 files read) · Size: S

Every statement is from reading the code (**observed**) unless marked **inferred**. Nothing was run. Structured version: `source.json`.

## Summary

Boardly is a small moderated forum. Members sign in with a cookie session, write posts of up to 5000 characters, and every post is stored as `pending` until a moderator publishes or rejects it from a moderation queue. Data uses uuid keys and a `status` column on posts. The db layer and the auth middleware are not in the folder, so their behaviour is partly unknown.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | sources/boardly | 2026-11-04 | 3 files, scanned (no findings), indexed, read; not run |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `sources/boardly/routes.js:1` | cookie sessions; every post waits for a moderator |
| A-E02 | A-R01 | observed | `sources/boardly/routes.js:2` | MAX_POST_LENGTH = 5000 |
| A-E03 | A-R01 | observed | `sources/boardly/routes.js:4` | POST /api/login sets session userId |
| A-E04 | A-R01 | observed | `sources/boardly/routes.js:5` | GET /api/posts/:id (session) |
| A-E05 | A-R01 | observed | `sources/boardly/routes.js:6` | POST /api/posts creates pending post |
| A-E06 | A-R01 | observed | `sources/boardly/routes.js:8` | GET /api/moderation (moderator) |
| A-E07 | A-R01 | observed | `sources/boardly/routes.js:9` | POST /api/moderation/:id sets status |
| A-E08 | A-R01 | observed | `sources/boardly/schema.sql:1` | users: uuid, email, display_name, role member/moderator |
| A-E09 | A-R01 | observed | `sources/boardly/schema.sql:2` | posts: uuid, author_id not null, body <= 5000, status |
| A-E10 | A-R01 | observed | `sources/boardly/client-routes.js:1` | client routes /posts, /moderation, /login |
| A-E11 | A-R01 | inferred | `sources/boardly/routes.js:5` | guard middleware used but not defined |

## Features

### A-F01 Email sign-in with cookie session
- **Source application:** Boardly (A) · **Evidence:** A-E01, A-E03, A-E08, A-E10
- **Description / behaviour:** POST /api/login checks credentials (db layer) and stores the user id in a server session.
- **Business logic:** credential check and password storage not visible.
- **Basis and confidence:** observed, medium

### A-F02 Read a post
- **Evidence:** A-E04 · GET /api/posts/:id behind a session returns {id, body, status}. Visibility of pending posts unknown. · observed, high

### A-F03 Create a post (pending until moderated)
- **Evidence:** A-E02, A-E05, A-E09 · max 5000 chars, author required, status starts `pending`. · observed, high

### A-F04 Moderation queue
- **Evidence:** A-E01, A-E06, A-E07, A-E09, A-E10, A-E11 · moderators list pending posts and set `published` or `rejected`; decision only validated by DB check. · observed, medium

### A-F05 Post list screen
- **Evidence:** A-E10 · a /posts screen exists but no list endpoint. · observed, low

## Screens and workflows

| Id | Screen | Route | Components | States seen | Evidence |
| --- | --- | --- | --- | --- | --- |
| A-S01 | PostList | `/posts` | unknown | none seen | A-E10 |
| A-S02 | ModerationQueue | `/moderation` | unknown | none seen | A-E10 |
| A-S03 | Login | `/login` | unknown | none seen | A-E10 |

**A-W01 Member posts:** A-S03 → A-S01. Edge cases: too long; stays pending.
**A-W02 Moderator clears queue:** A-S03 → A-S02. Edge cases: non-moderator refused (inferred).

## Navigation

Three client routes; no menu definition in the folder.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| User | id (uuid) | email (text, unique), display_name (text), role (text: member/moderator) | - | observed | A-E08 |
| Post | id (uuid) | author_id (uuid, not null), body (text <= 5000), status (pending/published/rejected), created_at (timestamptz) | author_id → User | observed | A-E09 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/login` | none | credentials | {ok} | unknown | A-E03 |
| GET | `/api/posts/:id` | session | - | {id, body, status} | unknown | A-E04 |
| POST | `/api/posts` | session | {body} | 201 post (pending) | DB check | A-E05 |
| GET | `/api/moderation` | moderator | - | pending posts | unknown | A-E06 |
| POST | `/api/moderation/:id` | moderator | {decision} | post | DB check | A-E07 |

## Authentication and authorization

Own users table, cookie session (`req.session.userId`), roles `member` and `moderator`, guards `requireSession` / `requireModerator` (definitions not present, inferred). Evidence A-E01, A-E03, A-E08, A-E11.

## Integrations

None found.

## Architecture and stack

Node.js Express-style backend (inferred from `app.get`/`req.session`), PostgreSQL-like SQL (uuid, timestamptz), client route table (framework unknown). No manifest.

## Configuration

None visible (session secret presumably configured elsewhere; unknown).

## Error handling

Failed login likely throws (result dereferenced unchecked); body length enforced by DB constraint.

## Unknowns

- Guard middleware and db layer are not in the folder.
- No list endpoint behind the /posts screen.
- Visibility of pending/rejected posts to non-authors.
- Frontend framework, packages.
- Nothing was run.
