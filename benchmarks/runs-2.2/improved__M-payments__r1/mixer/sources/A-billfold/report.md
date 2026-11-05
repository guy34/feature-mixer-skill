# Billfold (A): reverse-engineering report

App id: A · Access: own-code · Licence: not stated (no licence file, no rights in task.md) · Code reuse: unknown
Slice studied: the whole source (sources/billfold, 1 file) · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented** (the user's description in task.md), **inferred**, or **unknown**. The structured version of this report is `source.json` in the same folder.

## Summary

Billfold charges an order through an injected payment gateway and marks it paid on any webhook. It is two functions on an in-memory dict. The most important findings (observed): the fallback idempotency key is `str(id(order))`, which is not stable across retries; a gateway exception after a successful charge leaves the order unpaid; nothing stops a second charge with a new key; and every webhook delivery is applied again, whatever its type.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | `sources/billfold` | 2026-11-04 | scanned first (no findings); read in full |
| A-R02 | documentation | `task.md` | 2026-11-04 | the user's own description of the source, not the source's docs |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `sources/billfold/charges.py:1-2` | pay() calls gateway.charge(order['amount'], key or str(id(order))) and stores the returned charge id on the order |
| A-E02 | A-R01 | observed | `sources/billfold/charges.py:3` | pay() sets order['paid'] = True only after charge() returns; nothing catches a gateway error, and there is no check that the order is already paid |
| A-E03 | A-R01 | observed | `sources/billfold/charges.py:4-5` | on_webhook() sets order['paid'] = True on every delivery; it reads no event field (no id, no type) and its own comment says every delivery applies again |
| A-E04 | A-R02 | documented | `task.md#scenario-m` | The user describes Billfold as charging cards through a payment gateway and receiving its webhooks |

## Features

### A-F01 Charge an order through the payment gateway

- **Source application:** Billfold (A)
- **Evidence:** A-E01, A-E02, A-E04
- **Description:** Charges the order's amount through the gateway with an idempotency key and records the charge id
- **Observed behaviour:** pay(gateway, order, key) calls gateway.charge(amount, key or str(id(order))), stores charge_id, then sets paid = True
- **Business logic:** Idempotency key is the caller's key, else str(id(order)) (a process memory address, not stable across retries or processes). No already-paid check, so a second pay with a different key charges again. A gateway exception propagates and leaves paid unset even if the charge went through.
- **Data requirements:** Order.amount, Order.charge_id, Order.paid
- **Dependencies:** none
- **Integration requirements:** payment gateway adapter (charge with idempotency key)
- **Basis and confidence:** observed, high

### A-F02 Receive payment gateway webhooks

- **Source application:** Billfold (A)
- **Evidence:** A-E03, A-E04
- **Description:** Marks an order paid when the gateway sends a webhook
- **Observed behaviour:** on_webhook(order, event) sets paid = True; the event is not inspected
- **Business logic:** No deduplication by event id: every delivery (including retries) applies again. Event type is ignored, so a refund event would also mark the order paid.
- **Data requirements:** Order.paid
- **Dependencies:** A-F01
- **Integration requirements:** gateway webhook delivery
- **Basis and confidence:** observed, high

## Screens and workflows

None: the source is a library function with no screens, routes or user interface (observed).

## Navigation

None (observed: no routes or menus).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Order | none in the code (in-memory dict) | amount (number), charge_id (string), paid (boolean) | none | observed | A-E01, A-E02, A-E03 |

## API

No HTTP API (observed). Python entry points: `pay(gateway, order, key=None)`, `on_webhook(order, event)`.

## Authentication and authorization

None in the code (observed). No users, roles or permission checks.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| payment gateway | charge cards and deliver webhooks | A-F01, A-F02 | A-E01, A-E03, A-E04 |

## Architecture and stack

Python (plain functions, no framework); none: orders are in-memory dicts (observed). No packages, no manifest, no runtime pin.

## Configuration

None (observed: no settings or environment variables).

## Error handling

- gateway raises (for example a timeout after the charge went through): exception propagates; order keeps no charge id and paid stays unset although the gateway may have charged
- duplicate webhook delivery: applied again

## Unknowns

- Unit and currency of order['amount']: the code passes it straight to the gateway; the mock gateway names it amount_cents (from gateway.py, not from Billfold)
- How webhooks reach on_webhook (no HTTP endpoint or signature check in the code) and the event format (the code reads no field)
- Persistence: no store in the code; how Billfold saves orders is not shown
- Refunds: Billfold has no refund code
- Rights: task.md states no rights and there is no licence file, so code_reuse is unknown and nothing is copied
