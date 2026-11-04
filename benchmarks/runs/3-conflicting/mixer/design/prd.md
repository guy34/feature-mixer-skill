# Unified Community Forum: product requirements

Version: 2026-11-04 · Sources: A: Boardly, B: OpenForum · Status: approved (benchmark-operator, pre-approved in task)

## Problem

Two forums serve overlapping communities: Boardly (moderated, signed-in members) and OpenForum (open, immediate and anonymous posting). Running both splits the community and doubles upkeep. One forum keeps Boardly's moderation, makes published posts readable by anyone as OpenForum did, and brings both user bases and their posts into one place.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Visitor | read published posts | none (not signed in) |
| Member | write posts and see their status | member |
| Moderator | keep the forum clean | moderator |

## Core loop

1. A member signs in. 2. Writes a post; it is pending. 3. A moderator publishes or rejects it. 4. Anyone reads published posts in the list and on the post page.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Email sign-in with cookie session | A | improve | must | 401 on failure, argon2id, secret from config (U01) |
| M03 | Read a post (signed-in) | A | combine | must | with M04 as U02 |
| M04 | Read a post (public) | B | combine | must | published posts public; others author/moderator only |
| M05 | Create a post held for moderation | A | adapt | must | limit 10000 (U03) |
| M07 | Moderation queue | A | improve | must | server-validated decision, audit fields (U04) |
| M09 | Post list | A | rebuild | should | new list endpoint (U05) |

## User journeys

**J1 Post and get published:** /login → /posts/new → (pending) → moderator /moderation → publish → /posts. Features: M01, M05, M07, M09.
**J2 Visitor reads:** /posts → /posts/:id. Features: M09, M04.
**J3 Moderator rejects:** /login → /moderation → reject; the author still sees the post as rejected, visitors get 404. Features: M01, M07, M03.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given a user with a known email and password, when they POST /api/session, then a http-only session cookie is set and GET /api/session returns their id and role. |
| AC02 | M01 | Given a wrong password or unknown email, when they sign in, then 401 with {error:{code:"invalid_credentials"}} and no cookie. |
| AC03 | M05 | Given a signed-in member, when they POST a body of 1-10000 characters, then 201 with status pending and author_id = them. |
| AC04 | M05 | Given a body over 10000 characters or empty, then 422 and nothing is stored; without a session, 401. |
| AC05 | M04 | Given a published post, when a visitor GETs /api/posts/:id, then 200 with the unified contract. |
| AC06 | M03 | Given a pending or rejected post, when its author or a moderator GETs it, then 200; anyone else gets 404. |
| AC07 | M07 | Given a moderator, when they GET /api/moderation/queue, then pending posts oldest first; a member gets 403, a visitor 401. |
| AC08 | M07 | Given a pending post, when a moderator posts decision publish or reject, then status changes and moderated_by/at are set; any other decision gives 422; a decided post gives 409. |
| AC09 | M09 | Given published, pending and rejected posts, when anyone GETs /api/posts, then only published posts, newest first, with a cursor for the next page. |

## Non-functional requirements

Security: argon2id, http-only secure same-site cookies, CSRF protection on form posts, permission check on every handler and query, no personal data or secrets in logs. Accessibility: WCAG 2.2 AA for the five screens. Performance: list and post pages under 300 ms server time at 100k posts (indexes on status, created_at, author_id). Platforms: current desktop and mobile browsers.

## Out of scope

| Item | Why |
| --- | --- |
| M02 JWT bearer sign-in (B) | duplicate session mechanism; hard-coded key, no expiry |
| M06 Immediate publishing (B) | contradicts pre-moderation |
| M08 Anonymous posting (B) | incompatible with required author and moderation; could return as moderated anonymous posts |
| M10 Post list (B) | duplicate of M09 |
| Running the data migration | plan mode; plan approved only as a plan |
| Deployment | never automatic |

## Open questions

- Which former B admins should become moderators (listed at migration).
- Whether old OpenForum integer post links need redirects (no B clients known).
- Password hash formats in both sources (unknown; decides how many B users must reset).
