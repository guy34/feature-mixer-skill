# FileShare: product requirements

Version: 2026-11-04 · Sources: A: Uploader, B: Previewer, C: ShareLink · Status: approved (benchmark-operator, pre-approved in task)

## Problem

People need to put a file somewhere, check what is in it without downloading it, and hand it to someone
else safely. Uploader stores files, Previewer shows them, ShareLink shares them, but each is a fragment
with no common store, identity or permissions. One app joins the three steps on one File record with one
owner model.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Owner | upload, check, share and clean up their own files | user (signed in) |
| Recipient | open a file someone shared, with the password if one is set | link-holder (anonymous, token only) |

## Core loop

1. Sign in. 2. Upload a file (up to 10 MB). 3. Preview it. 4. Create a share link (expiry, optional password).
5. The recipient opens the link and previews or downloads the file.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Upload a file (10 MB limit) | A | adapt | must | stored in SQLite, owner from session |
| M02 | List my files | A | adapt | must | owner-scoped |
| M03 | Delete my file | A | adapt | should | cascades to share links |
| M04 | Text preview (first 20 lines) | B | adapt | must | .txt .md .csv |
| M05 | Image preview | B | improve | should | serves the original image; no thumbnails |
| M06 | No-preview fallback | B | adapt | must | every other type |
| M07 | Create share link with expiry | C | adapt | must | owner only, default 24 h |
| M08 | Password-protected link | C | improve | should | salted PBKDF2 |
| M09 | Open shared link | C | adapt | must | metadata, preview, download |
| M10 | Revoke share link | C | improve | should | owner only |

## User journeys

**J1 Share a file:** sign in → upload → preview → create link → recipient opens link → recipient downloads. Features: M01, M02, M04, M06, M07, M09.
**J2 Protect and withdraw:** create a password link → recipient enters password → owner revokes → link stops working. Features: M07, M08, M09, M10.
**J3 Clean up:** owner deletes a file → it leaves the list and its links stop working. Features: M02, M03, M09.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given a signed-in user, when they upload a file of at most 10 MB, then it is stored and returned with id, name and size (201). |
| AC02 | M01 | Given a signed-in user, when they upload more than 10485760 bytes, then the upload is refused with 413 and nothing is stored; exactly 10485760 bytes is accepted. |
| AC03 | M01 | Given no session, when anyone calls a file endpoint, then the answer is 401. |
| AC04 | M02 | Given two users with files, when each lists files, then each sees only their own. |
| AC05 | M03 | Given an owner's file with a share link, when the owner deletes it, then it leaves the list and the link answers 404; deleting another user's file answers 404 and changes nothing. |
| AC06 | M04 | Given a .txt, .md or .csv file (any case), when it is previewed, then the preview is kind text with at most the first 20 lines. |
| AC07 | M05 | Given a .png, .jpg or .gif file, when it is previewed, then the preview is kind image with a URL that serves the bytes with an image content type. |
| AC08 | M06 | Given any other file type, when it is previewed, then the preview is kind none with reason "no preview for this type". |
| AC09 | M07 | Given an owner's file, when they create a link, then it expires after 24 hours by default (or the hours given, which must be positive), other users cannot create links to it, and an expired link answers 404. |
| AC10 | M08 | Given a link with a password, when it is opened without or with a wrong password, then the answer is 403; with the right password it opens; the password is stored only as a salted slow hash. |
| AC11 | M09 | Given a valid link, when anyone opens it without signing in, then they get the file's name, size and preview and can download the bytes; an unknown token answers 404. |
| AC12 | M10 | Given a link, when the owner revokes it, then it answers 404; when another user tries to revoke it, then the answer is 404 and the link still works. |
| AC13 | M01, M04, M07, M09, M10 | Given a new user, when they register, upload, preview, share, the recipient opens the link, and the owner revokes it, then every step succeeds through the app's HTTP interface (in-process WSGI calls; no browser or socket) in that order. |

## Non-functional requirements

- Python 3 standard library only; SQLite; runs with `python3 -m fileshare`.
- Passwords (account and link) hashed with salted PBKDF2-HMAC-SHA256; sessions in http-only SameSite=Strict cookies.
- Every file read and write checks ownership in one place; no personal data or file contents in logs.
- Upload limit 10 MB enforced before reading the body (Content-Length).

## Out of scope

| Item | Why |
| --- | --- |
| Real image thumbnails (resizing) | needs an imaging library; standard library only (B's thumbnail URL is served with the original image instead) |
| Listing an owner's existing links | no source has it; tokens are shown once at creation |
| Deployment | not requested; never automatic |

## Open questions

- Should link expiry have an upper bound? No source sets one; none is enforced.
