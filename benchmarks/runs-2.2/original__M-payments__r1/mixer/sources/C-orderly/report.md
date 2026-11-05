# Orderly (C): reverse-engineering report

App id: C · Access: own-code · Licence: none stated (user's own source) · Code reuse: allowed
Slice studied: orders with states pending, paid, cancelled, refunded · Coverage: complete · Size: S

Structured version: `source.json` in this folder.

## Summary

Orderly is a 3-line Python module: a tuple of four order states and a `cancel(order)` function that
sets the status to cancelled. No transitions are enforced and a paid order is cancelled without a
refund (observed, and stated in the source comment).

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| C-R01 | local-directory | sources/orderly | 2026-11-05 | 1 file, 3 lines; scanned first (no findings) |
| C-R02 | documentation | task.md | 2026-11-05 | the user's one-line description |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| C-E01 | C-R01 | observed | `orders.py:1` | STATES = pending, paid, cancelled, refunded |
| C-E02 | C-R01 | observed | `orders.py:2-3` | cancel() sets cancelled unconditionally, no refund |
| C-E03 | C-R02 | documented | `task.md` | user's description of Orderly |

## Features

### C-F01 Order status lifecycle

- **Source application:** Orderly (C)
- **Evidence:** C-E01, C-E03
- **Description:** orders have one of four statuses.
- **Observed behaviour:** states defined only; no transition guard.
- **Business logic:** none enforced.
- **Data requirements:** Order.status
- **Dependencies:** none
- **Integration requirements:** payments must move pending -> paid; refunds paid -> refunded
- **Basis and confidence:** observed, high

### C-F02 Cancel an order

- **Source application:** Orderly (C)
- **Evidence:** C-E02, C-E03
- **Description:** cancel an order.
- **Observed behaviour:** status = cancelled regardless of current status; no refund.
- **Business logic:** no refund on paid orders; no guard for refunded/cancelled.
- **Data requirements:** Order.status
- **Dependencies:** C-F01
- **Integration requirements:** a refund path through the gateway (missing in source)
- **Basis and confidence:** observed, high

## Screens and workflows

None (library module).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Order | none (caller's dict) | status (pending/paid/cancelled/refunded) | - | observed | C-E01, C-E02 |

## API

No HTTP API; Python function `cancel(order)` and constant `STATES`.

## Authentication and authorization

None.

## Integrations

None.

## Architecture and stack

Plain Python (observed).

## Configuration

None.

## Error handling

None; invalid transitions are silently accepted (C-E02).

## Unknowns

- Where amounts and customers are stored: Orderly's code defines only status.
