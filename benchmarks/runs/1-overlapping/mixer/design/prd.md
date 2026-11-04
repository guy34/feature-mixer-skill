# Unified Notes: product requirements

Version: 2026-11-04 · Sources: A: QuickNotes, B: Jotter · Status: approved (benchmark-operator, pre-approved in task)

## Problem

The user has two small notes apps that each do half the job: QuickNotes
persists Markdown notes with shared tags, full title-and-body search and a
preview, but has no pinning or export; Jotter can pin and export but keeps
notes only in memory, searches titles only and stores labels as loose
strings. One app with persistent notes, tags, full search, preview, pinning
and Markdown export replaces both.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| The owner (single local user) | write, organise, find and export personal notes | owner |

## Core loop

1. Open the list (pinned notes on top).
2. Write or edit a note in Markdown and see it previewed.
3. Tag it, or pin it if it matters.
4. Find it later by search or tag.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Notes CRUD (persistent) | A | combine | must | U01 with M02 |
| M02 | Notes CRUD (status codes, uuid) | B | combine | must | U01 with M01 |
| M03 | Shared tags | A | adapt | must | U02; replaces B's labels |
| M05 | Search title and body | A | improve | must | U03; case-insensitive, escaped |
| M07 | Markdown preview | A | improve | should | U04; sanitised HTML |
| M08 | Pin notes | B | improve | should | U05; adds unpin |
| M09 | Export as Markdown | B | improve | should | U06; safe unique file names, front matter |

## User journeys

**J1 Capture a note:** list → new note → type title and Markdown → save → note appears at top of unpinned notes. Features: M01, M02.
**J2 Organise:** open note → add tag → pin → list shows it in the pinned section; filter by tag shows it. Features: M03, M08.
**J3 Find and read:** type a word from the body → result list → open → preview. Features: M05, M07.
**J4 Take notes out:** export → one Markdown file per note with front matter. Features: M09, M03.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given an empty store, when a note with title "A" is created, then the API returns 201 with a uuid id and the note survives an app restart. |
| AC02 | M02 | Given a note, when PUT sends `pinned` or `id`, then the API returns 400 and the note is unchanged; PUT with title refreshes updated_at. |
| AC03 | M01 | Given an unknown id, when it is read, updated or deleted, then the API returns 404 with the error shape. |
| AC04 | M01 | Given a note with title missing or longer than 200 characters, when it is created, then the API returns 400. |
| AC05 | M03 | Given a note, when tag "Work" is added twice and "work" once, then the note has one tag and the tags list has one "Work". |
| AC06 | M03 | Given a tagged note, when the note is deleted, then its note_tags rows are gone and the tag remains. |
| AC07 | M05 | Given notes "Groceries" (body "milk") and "Ideas", when searching "MILK", then only "Groceries" is returned; searching "%" matches only a literal %. |
| AC08 | M05 | Given any notes, when searching with an empty q, then the API returns 400. |
| AC09 | M07 | Given a body with `**bold**` and `<script>alert(1)</script>`, when previewed, then the HTML has `<strong>bold</strong>` and no script element. |
| AC10 | M08 | Given three notes, when the oldest is pinned, then it lists first; when unpinned, it returns to created_at order. |
| AC11 | M09 | Given two notes titled "a/b", when exported, then two distinct safe file names ending in .md are returned with title and tags in front matter. |

## Non-functional requirements

Local single-user app bound to 127.0.0.1; SQLite file persistence; responses
under 100 ms for 10,000 notes on a laptop; preview HTML always sanitised;
no personal note content in logs; keyboard-accessible UI with visible focus.

## Out of scope

| Item | Why |
| --- | --- |
| M04 Free-text labels (B) | dropped: replaced by shared tags (M03); labels migrate to tags |
| M06 Title-only search (B) | dropped: M05 searches titles too |
| Accounts and multi-user access | neither source has them; needed only if the app is hosted |
| Zip export download | B's comment mentions a zip that its code never built; open question |

## Open questions

- Should export be a zip download (Jotter's comment) or the JSON list (Jotter's code)?
- Is there live Jotter data to import? It lives only in a running process's memory.
- Will the app ever be hosted? If so, accounts and sessions must be added before it is.
