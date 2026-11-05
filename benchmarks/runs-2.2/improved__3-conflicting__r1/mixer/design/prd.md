# Unified Community Forum: product requirements

Version: 2026-11-04 · Sources: A: Boardly (own code), B: OpenForum (MIT) · Status: approved (benchmark operator, pre-approved)

## Problem

The user runs two small forums with opposite rules. Boardly (A) reviews
every post before anyone sees it but hides everything behind a sign-in and
leaks unreviewed posts to every member; OpenForum (B) is open to read and
post but publishes everything at once, allows anonymous posts and signs
tokens with a key written in its code. One community forum should be
readable by anyone, safe to post in (every post reviewed), and have one
account system.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Visitor | read the forum without an account | none (signed out) |
| Member | write posts and follow their review | member |
| Moderator | keep the forum free of spam and abuse | moderator (permission moderate-posts) |

## Core loop

1. A member signs in.
2. The member writes a post (up to 10000 characters); it is pending.
3. A moderator publishes or rejects it from the queue.
4. Anyone, signed in or not, reads published posts in the list and on the post page.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Sign in with a cookie session | A | improve | must | argon2id hashes, session expiry, logout, generic failure (U01) |
| M03 | Write a post (signed in, starts pending) | A | combine | must | with M04 (U02) |
| M04 | Write a post (up to 10000 characters) | B | combine | must | B's limit chosen (U02) |
| M05 | Pre-moderation queue | A | adapt | must | decisions validated and recorded (U03) |
| M08 | Read a post (members only) | A | combine | must | with M09: one read rule (U04) |
| M09 | Read a post (public) | B | combine | should | published posts only (U04) |
| M10 | Post list | A | rebuild | must | new list endpoint (U05) |

## User journeys

**J1 Post and get published:** Login → PostList (compose) → (moderator) ModerationQueue → visitor PostList → PostDetail. Features: M01, M03, M04, M05, M08, M09, M10.

**J2 Rejected post stays private:** member writes → moderator rejects → visitor and other members get 404; the author still sees it marked rejected. Features: M03, M05, M08, M09.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given a member with a password, when they sign in with it, then the response sets an http-only, SameSite=Lax session cookie; with a wrong password or unknown email the answer is the same 401 error. |
| AC02 | M01 | Given a signed-in member, when they sign out or the session passes its expiry, then the cookie no longer authenticates any request. |
| AC03 | M03, M04 | Given a signed-in member, when they post a body, then the answer is 201 with status pending and the member as author. |
| AC04 | M03, M04 | Given a signed-in member, when the body is 10000 characters it is accepted; when it is 10001 characters or empty the answer is 422 and nothing is stored. |
| AC05 | M03 | Given no session, when anyone posts, then the answer is 401 and nothing is stored. |
| AC06 | M05 | Given pending posts, when a moderator opens the queue and publishes one, then it becomes published and the decision records moderator and time; a member calling either endpoint gets 403. |
| AC07 | M05 | Given a post, when the decision is anything but published or rejected, the answer is 422; when the post is not pending, the answer is 409. |
| AC08 | M08, M09 | Given a published post, when a signed-out visitor opens it, then the answer is 200; given a pending post, the visitor gets 404. |
| AC09 | M08, M09 | Given a pending or rejected post, its author and any moderator can read it; another member gets 404. |
| AC10 | M10 | Given posts in every status, when anyone lists posts, then only published posts appear, newest first, 20 per page with a next cursor. |
| AC11 | M01 | Given users imported from B, when a former B admin signs in, then they are a member and cannot moderate. |
| AC12 | M01 | Given a request with an Authorization: Bearer header and no cookie, then it is treated as signed out. |
| AC13 | M01, M03, M05, M08, M09, M10 | Journey J1 end to end over HTTP: sign in, post, not visible to a visitor, moderator publishes, visitor sees it in the list and on its page. |
| AC14 | M03, M04 | Given the import rules, a new post with no author is refused by the database; an imported B post may have no author and is stored as published with imported_from = 'B'. |
| AC15 | M03 | Given any post, created_at is stored and returned in UTC. |

## Non-functional requirements

Security: argon2id, http-only secure cookies, CSRF protection on state-changing
requests (SameSite=Lax plus a CSRF token), server-side validation, one
authorisation function, no personal data or secrets in logs, rate limiting on
sign-in. Accessibility: WCAG 2.2 AA for the four screens. Performance: list
and detail under 200 ms at p95 for 100k posts (indexes on status, created_at).
Platforms: current desktop and mobile browsers.

## Out of scope

| Item | Why |
| --- | --- |
| M02 Sign in with a bearer token (B) | dropped: one session mechanism; B's key was hard-coded |
| M06 Instant publishing (B) | dropped: incompatible with pre-moderation (M05) |
| M07 Anonymous posting (B) | deferred: needs abuse protection; would go through moderation |
| M11 Post list (B) | duplicate of M10 |
| Account sign-up | neither source shows how accounts are created (not invented) |

## Open questions

- How are accounts created? Neither source has sign-up; an operator command or an invitation flow needs the user's decision.
- B's server time zone, needed to convert B's naive timestamps before any import.
- Is there real data in either app to migrate? Unknown; the migration plans are approved as plans only.
- How B stored passwords is unknown; imported B users may need a password reset.
