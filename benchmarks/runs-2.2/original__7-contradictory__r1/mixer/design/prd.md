# Shelfie + Readr unified reading app: product requirements

Version: 2026-11-04 · Sources: A: Shelfie, B: Readr · Status: approved (benchmark operator, pre-approved)

## Problem

People want one place to keep their books, rate them and group them into reading lists. Shelfie has a library and
ratings but no lists; Readr has lists but no interface and no way to see anything. Neither has accounts, and both
lose their writes (no commit). Shelfie's documentation also promises things its code never did (CSV export, 1-10
ratings, PostgreSQL, three services). The unified app is built on what the code actually does, with those gaps fixed.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Reader | Keep a personal library, rate books, plan reading in lists, take their data with them | reader (owns only their own records) |

## Core loop

1. Sign in. 2. Add a book (title, optional author). 3. Rate it 1-5 stars. 4. Put it on a reading list. 5. See the library and lists with ratings.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Personal library | A | improve | must | adds create/edit/delete and ownership (Shelfie only listed books) |
| M02 | Star ratings 1-5 | A | improve | must | one rating per user per book; 1-5 as both codebases do, not the documented 1-10 |
| M04 | Library export (JSON) | A | improve | should | JSON as the code does; one row per book; documented CSV not built |
| M05 | Reading lists | B | improve | must | adds create/rename/delete/view/remove; no duplicates |

Platform (no menu id): accounts and sessions, which no source had.

## User journeys

**J1 Build and rate a library:** sign up → add book → rate 4 stars → change to 5 → see it in the library. Features: M01, M02.
**J2 Plan reading:** create list "Summer" → add two books → remove one → rename the list → delete a book (it leaves the list). Features: M05, M01.
**J3 Take my data:** export → JSON file with every book once and its current rating. Features: M04, M01, M02.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given a signed-in user, when they add a book with a title (author optional), then it appears in their library and nobody else's. |
| AC02 | M01 | Given a book, when its owner edits or deletes it, then the change is saved and persists across a restart; a blank title is rejected with 400. |
| AC03 | M01 | Given user B, when B requests, edits or deletes user A's book by id, then the response is 404 and nothing changes. |
| AC04 | M02 | Given a book in the user's library, when they rate it 1-5, then exactly one rating is stored; rating again replaces it; clearing removes it. |
| AC05 | M02 | Given any rating request, when stars is 0, 6, 10, 3.5, "3" or true, then the response is 400 invalid_stars and nothing is stored (the documented 1-10 scale is not accepted). |
| AC06 | M04 | Given a library with rated and unrated books, when the user exports, then they get a JSON attachment with one object per own book {id, title, author, stars|null} and no other user's books. |
| AC07 | M05 | Given a signed-in user, when they create, rename and delete lists, then names are required, unique per user, and deleting a list keeps its books. |
| AC08 | M05 | Given a list, when the user adds the same book twice, then it appears once; adding another user's book or to another user's list returns 404. |
| AC09 | M05, M01 | Given a book on a list, when the book is deleted, then it disappears from the list (cascade). |
| AC10 | accounts | Given no session, when any /api/v1 endpoint other than signup or login is called, then the response is 401 in the standard error shape; wrong passwords return 401; sign-out ends the session. |

## Non-functional requirements

Security: passwords hashed with scrypt; http-only SameSite=Lax session cookies, Secure in production; CSRF token on
state-changing requests; ownership check on every read and write; no personal data or secrets in logs. Durability:
every write in a committed transaction; foreign keys enforced. Accessibility: forms with labels, star input as a
keyboard-usable radio group, WCAG AA contrast. Performance: list pages under 200 ms for 5,000 books on SQLite.
Platform: any modern browser; Python 3.10+.

## Out of scope

| Item | Why |
| --- | --- |
| M03 Readr's rating function | dropped: identical to M02, which is kept |
| CSV export at /api/v1/books/export.csv | only in Shelfie's stale README/spec; the code never had it (user: trust the code). Open question |
| 1-10 rating scale / `score` field | only in Shelfie's stale docs; both codebases use 1-5 |
| Three-service architecture, PostgreSQL | only in Shelfie's stale docs; not needed (see architecture) |
| Importing data from shelfie.db / readr.db | existence of data unknown; would need its own approved migration (see migration-plan.md) |
| Sharing lists, social features, admin role | in no source |

## Open questions

- Does the user want CSV export as a new feature (the old docs promised it)? It would be an added option on M04.
- Is there real data in shelfie.db or readr.db that should be imported (see migration-plan.md for the risks)?
- Single-user (no accounts) would also satisfy the task; the plan assumes several people, as task.md says "people".
