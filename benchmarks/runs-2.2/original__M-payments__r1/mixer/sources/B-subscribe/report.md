# Subscribe (B): reverse-engineering report

App id: B · Access: own-code · Licence: none stated (user's own source) · Code reuse: allowed
Slice studied: monthly subscriptions that create orders · Coverage: complete · Size: S

Structured version: `source.json` in this folder.

## Summary

Subscribe is a 2-line Python module. `renew(subscription, create_order)` creates one order for the
subscription's customer at its price through an injected callback. It does not charge, schedule, or
track periods (observed); "monthly" comes only from the user's description (documented).

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | sources/subscribe | 2026-11-05 | 1 file, 2 lines; scanned first (no findings) |
| B-R02 | documentation | task.md | 2026-11-05 | the user's one-line description |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `plans.py:1-2` | renew() returns create_order(customer, price) |
| B-E02 | B-R02 | documented | `task.md` | subscriptions are monthly and create orders |

## Features

### B-F01 Renew a subscription into an order

- **Source application:** Subscribe (B)
- **Evidence:** B-E01, B-E02
- **Description:** each renewal creates a new order for the customer at the subscription price.
- **Observed behaviour:** calls the injected `create_order(customer, price)` and returns its result.
- **Business logic:** price copied at renewal; no period tracking or double-renewal guard in code.
- **Data requirements:** Subscription.customer, Subscription.price
- **Dependencies:** an order-creation function
- **Integration requirements:** order creation from the unified order module
- **Basis and confidence:** observed, high

## Screens and workflows

None (library module).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Subscription | none (caller's dict) | customer (any), price (number) | creates Order via callback | observed | B-E01 |

## API

No HTTP API; Python function `renew(subscription, create_order)`.

## Authentication and authorization

None.

## Integrations

None besides the injected order-creation callback.

## Architecture and stack

Plain Python; order creation injected (observed).

## Configuration

None.

## Error handling

None: errors from create_order propagate.

## Unknowns

- Renewal scheduling and period identity: not in the code.
- Units of `price`: assumed cents to match task.md's create_order(customer, amount_cents).
