# Billfold (A): reverse-engineering report

App id: A · Access: own-code · Licence: none stated (user's own source) · Code reuse: allowed
Slice studied: charging through a payment gateway and receiving its webhooks · Coverage: complete · Size: S

Structured version: `source.json` in this folder.

## Summary

Billfold is a 5-line Python module with two functions. `pay()` charges an order's amount through an
injected gateway with an idempotency key and marks the order paid; `on_webhook()` marks the order paid
on every delivery. Key findings (observed): the fallback idempotency key is `str(id(order))`, which is
not stable; gateway errors (including a timeout after a successful charge) are not handled; webhooks are
never de-duplicated and their type is ignored.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | sources/billfold | 2026-11-05 | 1 file, 5 lines; scanned first (no findings) |
| A-R02 | documentation | task.md | 2026-11-05 | the user's one-line description |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `charges.py:1-3` | pay() charges via gateway.charge(amount, key), stores charge_id, sets paid |
| A-E02 | A-R01 | observed | `charges.py:2` | fallback key `str(id(order))` is a per-process object address |
| A-E03 | A-R01 | observed | `charges.py:4-5` | on_webhook() sets paid on every delivery, ignores event id/type |
| A-E04 | A-R01 | observed | `charges.py:2-3` | no error handling around gateway.charge |
| A-E05 | A-R02 | documented | `task.md` | user's description of Billfold |

## Features

### A-F01 Charge an order through the payment gateway

- **Source application:** Billfold (A)
- **Evidence:** A-E01, A-E02, A-E04, A-E05
- **Description:** charge the order amount and record the charge id.
- **Observed behaviour:** `gateway.charge(order["amount"], key or str(id(order)))`, then `charge_id` set, `paid=True`.
- **Business logic:** idempotency delegated to the gateway key; no unpaid check; no timeout handling.
- **Data requirements:** Order.amount, Order.charge_id, Order.paid
- **Dependencies:** none
- **Integration requirements:** gateway with `charge(amount, key)`
- **Basis and confidence:** observed, high

### A-F02 Receive payment gateway webhooks

- **Source application:** Billfold (A)
- **Evidence:** A-E03, A-E05
- **Description:** apply a gateway event to an order.
- **Observed behaviour:** sets `paid=True` on every delivery.
- **Business logic:** no de-duplication, no event-type dispatch, no state check.
- **Data requirements:** Order.paid
- **Dependencies:** A-F01
- **Integration requirements:** event delivery from the gateway; order lookup
- **Basis and confidence:** observed, high

## Screens and workflows

None: Billfold is a library module with no UI or routes (observed).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Order | none (caller's dict) | amount (number), charge_id (str), paid (bool) | - | observed | A-E01, A-E03 |

## API

No HTTP API; Python functions `pay(gateway, order, key=None)` and `on_webhook(order, event)` (observed).

## Authentication and authorization

None in the code (observed). Webhook signature verification is absent.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| Payment gateway | charge(amount, key) -> charge id; webhook events | A-F01, A-F02 | A-E01, A-E03 |

## Architecture and stack

Plain Python functions mutating caller-owned dicts; no persistence, no framework (observed).

## Configuration

None.

## Error handling

Gateway exceptions propagate and leave the order without charge_id even if the charge succeeded (A-E04).
Duplicate webhooks are re-applied (A-E03).

## Unknowns

- Webhook event schema: never read by the code; known only from task.md.
- Units of `amount`: not stated; task.md uses cents.
