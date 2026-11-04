# BookNow (A): reverse-engineering report

App id: A · Access: own-code · Licence: proprietary (user's own) · Code reuse: allowed
Slice studied: book, pay, cancel · Coverage: partial · Size: S

Every statement below is marked with its basis where it is not obvious. The structured version is `source.json`.

## Summary

BookNow lets a user book a slot, pay for it by card through Stripe, and cancel up to 24 hours before the slot starts. The folder holds only `bookings.py` and a README: booking checks a `taken` flag, charges the price, then writes a booking; cancelling enforces the 24-hour window and hard-deletes the booking without a refund. The payments module, the database layer, auth and any UI are not included, so coverage is partial.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | sources/booknow | 2026-11-04 | 2 files; not a git repo; nothing run |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | documented | `README.md:2` | book, cancel 24h before, pay by card (Stripe) |
| A-E02 | A-R01 | observed | `bookings.py:5` | book(): taken check, charge, insert |
| A-E03 | A-R01 | observed | `bookings.py:12` | cancel(): <24h refused, else hard delete |
| A-E04 | A-R01 | observed | `bookings.py:3` | imports charge from payments, which is missing |
| A-E05 | A-R01 | observed | `bookings.py:9` | charge before insert; no refund on cancel |
| A-E06 | A-R01 | inferred | `bookings.py:6` | storage via injected db object; engine unknown |

## Features

### A-F01 Book a slot

- **Source application:** BookNow (A)
- **Evidence:** A-E01, A-E02
- **Description:** book one open slot, paid at booking time
- **Observed behaviour:** taken → error; else charge price, insert booking
- **Business logic:** taken slots refused; slot.taken is never set here
- **Data requirements:** Slot(taken, price), Booking(user_id, slot_id, created_at)
- **Dependencies:** A-F03
- **Integration requirements:** users, slots, payments
- **Basis and confidence:** observed, high

### A-F02 Cancel a booking up to 24 hours before

- **Source application:** BookNow (A)
- **Evidence:** A-E01, A-E03, A-E05
- **Description:** cancel when the slot starts at least 24 hours from now
- **Observed behaviour:** <24h → PermissionError; else delete row
- **Business logic:** 24h window; hard delete; no refund
- **Data requirements:** Booking, Slot.starts_at
- **Dependencies:** A-F01
- **Integration requirements:** refund policy with payments
- **Basis and confidence:** observed, high

### A-F03 Pay by card (Stripe)

- **Source application:** BookNow (A)
- **Evidence:** A-E01, A-E04, A-E05
- **Description:** charge slot price by card via Stripe at booking
- **Observed behaviour:** only the call `charge(user_id, price)`; implementation missing
- **Business logic:** amount = slot.price; everything else unknown
- **Data requirements:** Slot.price
- **Dependencies:** none seen
- **Integration requirements:** Stripe (test mode; keys by name only)
- **Basis and confidence:** observed (call site), medium

## Screens and workflows

No screens or routes in the source.

## Navigation

None in the source.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Slot | id (unknown) | taken (bool, inferred), price (unknown), starts_at (datetime) | - | observed | A-E02, A-E03 |
| Booking | id (unknown) | user_id, slot_id, created_at (naive UTC datetime) | slot_id → Slot | observed | A-E02, A-E03 |

## API

No HTTP API in the source; only Python functions `book(db, user_id, slot_id)` and `cancel(db, booking_id, now=None)`.

## Authentication and authorization

Unknown: `user_id` is passed in; no auth code present.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| Stripe | card payment | A-F03 | A-E01, A-E04 |

## Architecture and stack

Python; abstract `db` object (observed); payments module missing.

## Configuration

None visible. Stripe keys would be needed by name only (e.g. `STRIPE_SECRET_KEY`), inferred.

## Error handling

Slot taken → ValueError; late cancel → PermissionError; payment failure unknown; no compensation if insert fails after charge.

## Unknowns

- payments.py missing: Stripe usage, failures, refunds unknown.
- db layer and schema missing.
- Nothing sets slot.taken: possible double-booking gap.
- No auth, slot creation, API or UI.
- No rollback if insert fails after a successful charge.
