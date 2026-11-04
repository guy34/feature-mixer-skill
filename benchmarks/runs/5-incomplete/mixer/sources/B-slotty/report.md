# Slotty (B): reverse-engineering report

App id: B · Access: closed · Licence: proprietary · Code reuse: not-allowed
Slice studied: publish, book (incl. recurring), waiting list, calendar sync · Coverage: partial · Size: M

Read only from the provided copy of Slotty's public overview and API spec. Nothing was run or fetched. The structured version is `source.json`.

## Summary

Slotty lets teams publish open slots and customers book them, optionally as a weekly recurring booking for up to 12 weeks, join a waiting list when a slot is full, and sync bookings with a calendar. Only a short overview and a two-path API spec were available. The calendar sync page the overview links to (calendar.md) was not provided, and the spec has no schemas, auth or errors, so coverage is partial and most contracts are inferred.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | documentation | sources/slotty-docs/overview.md | 2026-11-04 | links to calendar.md, which is missing |
| B-R02 | api-spec | sources/slotty-docs/openapi.yaml | 2026-11-04 | OpenAPI 3.0.3, summaries only |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | documented | `overview.md:3` | teams publish slots; customers book |
| B-E02 | B-R01 | documented | `overview.md:5` | weekly recurring, up to 12 weeks |
| B-E03 | B-R01 | documented | `overview.md:6` | calendar sync exists |
| B-E04 | B-R01 | unknown | `calendar.md` | linked page not provided |
| B-E05 | B-R01 | documented | `overview.md:7` | waiting list when full |
| B-E06 | B-R02 | documented | `openapi.yaml#/paths/~1bookings/post` | create booking, optionally recurring |
| B-E07 | B-R02 | documented | `openapi.yaml#/paths/~1waitlist/post` | join waiting list |
| B-E08 | B-R02 | inferred | `openapi.yaml#/paths` | no other endpoints published |

## Features

### B-F01 Publish open slots
- **Source application:** Slotty (B) · **Evidence:** B-E01, B-E08
- **Description:** teams publish open slots · **Business logic:** not documented
- **Basis and confidence:** documented, medium

### B-F02 Book a slot
- **Source application:** Slotty (B) · **Evidence:** B-E01, B-E06
- **Description:** customer books an open slot via POST /bookings · **Dependencies:** B-F01
- **Basis and confidence:** documented, medium

### B-F03 Recurring bookings
- **Source application:** Slotty (B) · **Evidence:** B-E02, B-E06
- **Description:** same slot weekly, up to 12 weeks · **Business logic:** weekly; max 12; partial-availability and series cancel undocumented
- **Basis and confidence:** documented, medium

### B-F04 Calendar sync
- **Source application:** Slotty (B) · **Evidence:** B-E03, B-E04
- **Description:** keeps bookings in step with a calendar · **Business logic:** unknown (calendar.md missing)
- **Basis and confidence:** documented (existence only), low

### B-F05 Waiting list
- **Source application:** Slotty (B) · **Evidence:** B-E05, B-E07
- **Description:** join a waiting list when a slot is full · **Business logic:** what happens on release undocumented
- **Basis and confidence:** documented, medium

## Screens and workflows

No screens available (no browser use, no screenshots provided).

## Navigation

Unknown.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Slot | unknown | unknown | - | inferred | B-E01 |
| Booking | unknown | recurring option | → Slot (inferred) | inferred | B-E06 |
| WaitlistEntry | unknown | unknown | → Slot (inferred) | inferred | B-E07 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/bookings` | unknown | unknown (optionally recurring) | unknown | unknown | B-E06 |
| POST | `/waitlist` | unknown | unknown | unknown | unknown | B-E07 |

## Authentication and authorization

Not documented. Two audiences are implied (teams, customers).

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| Calendar (unspecified) | sync bookings | B-F04 | B-E03, B-E04 |

## Architecture and stack

Not documented (closed product).

## Configuration

Not documented.

## Error handling

Not documented.

## Unknowns

- calendar.md missing: calendar sync providers, direction, conflicts.
- API spec has no schemas, auth or errors.
- No publish, list, cancel or waitlist-management endpoints.
- No payment or cancellation policy.
- Waiting-list release behaviour.
- Recurring: partial availability, series cancellation.
- Auth, roles, stack.
