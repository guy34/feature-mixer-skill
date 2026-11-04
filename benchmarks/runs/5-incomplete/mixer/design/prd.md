# Unified booking app: product requirements

Version: 2026-11-04 · Sources: A: BookNow (own code), B: Slotty (closed; public docs and API spec only) · Status: approved (benchmark-operator, pre-approved in task)

## Problem

Teams need to publish bookable slots, and customers need to book and pay for them, cancel safely, book the same slot weekly, and get a chance at full slots. BookNow has paid booking and a 24-hour cancellation rule but no slot publishing, recurrence or waiting list; Slotty documents publishing, recurrence and a waiting list but no payments. One app combines both.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Customer | find an open slot, book and pay, cancel or rebook | customer |
| Team member | publish and manage slots | staff |

## Core loop

1. Staff publishes a slot. 2. Customer signs in and picks an open slot. 3. Customer pays by card; the booking is confirmed. 4. Customer sees it under My bookings, and may cancel 24h+ before for a full refund.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M05 | Publish open slots | B | rebuild | must | U01; closed source, rebuilt from docs |
| M04 | Pay by card (Stripe) | A | rebuild | must | U02; source charge() missing |
| M01 | Book a slot (pay at booking) | A | improve | must | U03; atomic hold, charge, confirm |
| M03 | Cancel up to 24 hours before | A | improve | must | U04; soft cancel, full refund |
| M06 | Recurring weekly bookings | B | rebuild | should | U05; 2-12 weeks, all-or-nothing |
| M08 | Waiting list | B | rebuild | should | U06; offers with 2h hold |

## User journeys

**J1 Book and pay:** open slots → slot detail → pay → My bookings. Features: M05, M01, M04.
**J2 Cancel:** My bookings → cancel (24h+) → refund shown. Features: M03, M04.
**J3 Book weekly:** slot detail → book weekly (n weeks) → pay all → series in My bookings. Features: M06, M01, M04.
**J4 Wait for a full slot:** slot detail (taken) → join waiting list → offer → accept and pay. Features: M08, M01, M04.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M05 | Given a staff user, when they create and publish a future slot, then it appears in the open-slot list; customers cannot create slots (403). |
| AC02 | M01 | Given an open slot, when a customer books and the test charge succeeds, then one confirmed booking exists and the slot is no longer open. |
| AC03 | M01 | Given a slot with a confirmed booking, when another customer books it, then the request fails with 'slot taken' and no charge is made. |
| AC04 | M04 | Given a declined test card, when a customer books, then no booking remains and the slot is open again. |
| AC05 | M04 | Given a retried booking request with the same idempotency key, then Stripe is charged once. |
| AC06 | M03 | Given a booking starting in 25 hours, when the owner cancels, then it becomes cancelled, a full refund is recorded and the slot reopens. |
| AC07 | M03 | Given a booking starting in 23 hours, when the owner cancels, then it is refused with 'too late to cancel'. |
| AC08 | M06 | Given 12 free weekly slots, when a customer books a 12-week series, then 12 confirmed bookings and 12 charges exist; 13 weeks is refused. |
| AC09 | M06 | Given one taken week, when a series is requested, then nothing is booked or charged and the taken weeks are listed. |
| AC10 | M08 | Given a taken slot with two waiting customers, when the booking is cancelled, then only the first gets an offer with a 2-hour hold; on expiry the second gets it. |
| AC11 | M08 | Given an offer, when the customer accepts and pays, then they hold a confirmed booking and leave the list. |

## Non-functional requirements

Server-side validation and a permission check on every read and write; passwords hashed with a slow hash; http-only session cookies and CSRF protection; no personal data or secrets in logs; Stripe in test mode until the user supplies live keys; WCAG 2.1 AA contrast and keyboard use; modern desktop and mobile browsers.

## Out of scope

| Item | Why |
| --- | --- |
| M02 Book a slot (Slotty API) | dropped: duplicate of M01 with weaker evidence |
| M07 Calendar sync | deferred: could, low confidence; calendar.md not provided; needs an external calendar API |
| Saved cards / off-session charges | not needed by D01 |
| Deployment | plan mode; never automatic |

## Open questions

- Currency and price format of BookNow's existing data (payments.py and db were not provided).
- Whether BookNow already refunds somewhere in the missing payments.py (D02 assumes not).
- Waiting-list hold length (2 hours chosen as a default, D03).
- Calendar provider and sync direction if M07 is revived.
