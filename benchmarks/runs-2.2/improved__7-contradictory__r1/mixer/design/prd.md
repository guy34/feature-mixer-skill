# Shelfie + Readr reading app: product requirements

Version: 2026-11-04 · Sources: A: Shelfie, B: Readr · Status: approved (benchmark operator, pre-approved)

## Problem

People want one place to keep the books they own or read, rate them, and
group them into reading lists. Shelfie can list and rate books and export
them, but has no way to add books and no lists; Readr has reading lists and
ratings but no interface and no way to create lists. Neither has users or
saves its writes reliably. One app with one library, one rating scale and
full reading lists covers the whole loop. Where Shelfie's old documentation
disagrees with its code (CSV export, 1-10 ratings, PostgreSQL, three
services), this product follows the code, as the user asked.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Reader | keep a personal library, rate books, make reading lists | member (owns their own data only) |

## Core loop

1. Sign in.
2. Add a book (title, optional author).
3. Rate it 1-5 stars.
4. Put it on a reading list.
5. See the library and lists; export when wanted.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Book library | A | improve | must | adds add/edit/remove (Shelfie only lists); per person |
| M02 | Rate a book 1-5 stars | A (B identical, dropped) | improve | must | one rating per person per book, replaceable, clearable |
| M04 | Export library (JSON) | A | adapt | could | [{title, stars}] for your own books; no CSV |
| M05 | Reading lists | B | improve | must | create, view, rename, delete, add/remove books; no duplicates |

## User journeys

**J1 Build a library and a reading list:** sign up → add book → rate it → create list → add book to list → view list → export. Features: M01, M02, M05, M04.

**J2 Tidy up:** change a rating → remove a book from a list → delete a book (its rating and list entries go with it). Features: M01, M02, M05.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given a signed-in person, when they add a book with a title (author optional), then it appears in their library; editing changes it; removing deletes it; a missing or empty title gives 400. |
| AC02 | M01 | Given two people, when the second asks for, rates, lists, edits or deletes the first person's book or list, then the answer is 404 and nothing changes; neither sees the other's books, lists or export. |
| AC03 | M02 | Given a book, when it is rated with 1, 2, 3, 4 or 5 the rating is saved; 0, 6, 3.5, "5" or a missing value gives 400 and nothing is saved. |
| AC04 | M02 | Given a rated book, when it is rated again the new value replaces the old one (one rating per person per book), and clearing removes it. |
| AC05 | M04 | Given books with and without ratings, when export is requested, then the response is JSON [{title, stars}] with one entry per book and stars null when unrated. |
| AC06 | M05 | Given a signed-in person, they can create a list (name required), rename it, view it with its books, add and remove their own books, and delete it (books stay in the library). |
| AC07 | M05 | Adding a book already on a list leaves one entry; adding an unknown or another person's book or list gives 404. |
| AC08 | M01 | Every /api endpoint except sign up and sign in answers 401 without a valid session; sign out ends the session. |
| AC09 | M01 | Data written before a restart is there after it; deleting a book removes its rating and list entries. |
| AC10 | M01 | Journey J1 works end to end over HTTP. |

## Non-functional requirements

- Security: passwords hashed with scrypt; http-only session cookie; every query filtered by owner; server-side validation; no personal data or secrets in logs.
- Data: every write committed; foreign keys enforced.
- Accessibility: keyboard-operable star rating and forms, visible focus, labels on every field.
- Platforms: current desktop and mobile browsers; Python 3.10+ server.
- No third-party packages.

## Out of scope

| Item | Why |
| --- | --- |
| M03 Readr's rating | identical to M02; dropped as a duplicate |
| CSV export | documented in Shelfie's README/spec only; the code exports JSON (user: trust the code) |
| 1-10 rating scale, 'score' field | documented only; both apps' code use 1-5 'stars' |
| /api/v1 prefix, PostgreSQL, three-service gateway | documented only; not what Shelfie's code does |
| Importing existing shelfie.db / readr.db data | none provided; needs its own migration plan and approval |
| Rating history, shared catalogue, sharing lists | in no source and not asked for |
| Deployment | plan mode; never automatic |

## Open questions

- Is the app for several people (as designed, with accounts) or one person on one machine (accounts could be dropped)?
- Does the user have real data in shelfie.db or readr.db to import?
- Does the user want CSV export after all (the old docs promised it)?
- Were appended ratings (a history) intended in either source?
