# Unified CRM: product requirements

Version: 2026-11-04 · Sources: A: MegaCRM, B: DealFlow · Status: approved (benchmark-operator, pre-approved in task)

## Problem

The team has contacts and a fixed-stage pipeline in MegaCRM and a
configurable pipeline with stale-deal reminders in DealFlow. Neither has
users, a UI or real persistence. One CRM gives them contacts, deals that move
through stages they configure, duplicate cleanup, exports, and reminders so
deals do not go quiet, in one place with one login.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Sales rep | track contacts and own deals through the pipeline | member |
| Sales lead / admin | configure stages, clean up duplicates, manage users | admin |

## Core loop

1. Sign in. 2. Find or add a contact. 3. Create a deal for them. 4. Move the
deal through the stages as it progresses. 5. Get an email when a deal has
sat still too long.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Contact management | A | adapt | must | U01; A's logic on Django models |
| M02 | Merge duplicate contacts | A | improve | should | U02; transactional, audited, admin only |
| M03 | Deals pipeline (fixed stages) | A | combine | must | U03 with M04; A's deal record and default stages |
| M04 | Deals pipeline (custom stages) | B | combine | must | U03 with M03; configurable stages, moved_at |
| M05 | CSV export | A | improve | should | U04; header row, fixed export list |
| M06 | Stale-deal reminders | B | improve | should | U05; skip closed stages, dedupe |

## User journeys

**J1 Track a deal:** sign in → /contacts (search or add) → /contacts/{id} → new deal → /deals board → move it. Features: M01, M03, M04.
**J2 Clean up a duplicate:** /contacts/{id} → Merge → pick the duplicate → confirm → deals now under the kept contact. Features: M02.
**J3 Export:** /exports → contacts.csv or deals.csv. Features: M05.
**J4 Stale reminder:** daily job → owner receives one email for a deal idle 14+ days → owner moves the deal. Features: M06, M04.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given a signed-in member, when they add a contact with a name and an email, then it is listed and found by searching part of the name or email. |
| AC02 | M01 | Given a contact with email x@y.z, when another contact is saved with X@Y.Z, then it is rejected as a duplicate email. |
| AC03 | M03 | Given a new install, when stages are listed, then lead, qualified, proposal, won, lost and closed exist in that order with won/lost/unspecified outcomes. |
| AC04 | M04 | Given an admin adds a stage "demo", when a deal is moved to it, then the move succeeds and moved_at is set to now (UTC). |
| AC05 | M03 | Given a deal, when it is moved to a stage that is not configured or is inactive, then the API returns 400 with error code unknown_stage and the deal is unchanged. |
| AC06 | M02 | Given contacts K and D where D has two deals, when an admin merges D into K, then both deals belong to K, K's empty fields are filled from D, D is gone, a ContactMerge entry exists, and the deals' moved_at is unchanged. |
| AC07 | M02 | Given a merge that fails part-way, then no deal or contact has changed. |
| AC08 | M02 | Given a member (not admin), when they call merge, then the API returns 403. |
| AC09 | M05 | Given contacts and deals, when deals.csv is downloaded, then the first row is a header and each deal row has stage, moved_at and owner email. |
| AC10 | M05 | Given any export name other than contacts or deals, then the API returns 404. |
| AC11 | M06 | Given an open deal unmoved for 15 days and REMINDER_STALE_DAYS=14, when the job runs twice, then its owner gets exactly one email. |
| AC12 | M06 | Given a won, lost or closed deal unmoved for 30 days, when the job runs, then no email is sent. |

## Non-functional requirements

Server-side validation on every write; can(user, action, record) on every
read and write; passwords hashed with Django's slow hashers; sessions in
http-only secure cookies with CSRF; no personal data or secrets in logs;
WCAG 2.1 AA for the pages; modern desktop and mobile browsers.

## Out of scope

| Item | Why |
| --- | --- |
| Contact notes | mentioned in A's merge docstring only; no notes feature exists in either source |
| React UI from A | declared in package.json, no UI source; replaced by server-rendered pages (D02) |
| Multiple pipelines | neither source has them; one configurable pipeline covers both |
| Running the data migration | plan mode; migration plan approved as a plan only |
| Deployment | not requested |

## Open questions

- Is there real MegaCRM or DealFlow data to import? Neither source has a working database.
- Who is the default owner for A's existing deals?
- Which SMTP provider and hosting should be used?
