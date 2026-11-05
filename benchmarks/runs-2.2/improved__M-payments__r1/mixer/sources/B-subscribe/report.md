# Subscribe (B): reverse-engineering report

App id: B · Access: own-code · Licence: not stated (no licence file, no rights in task.md) · Code reuse: unknown
Slice studied: the whole source (sources/subscribe, 1 file) · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented** (the user's description in task.md), **inferred**, or **unknown**. The structured version of this report is `source.json` in the same folder.

## Summary

Subscribe renews a subscription by calling an injected `create_order(customer, price)` and returning the result. It is one function. Observed: there is no billing period and no duplicate check, so two renewals for the same month create two orders. The monthly schedule exists only in the user's description (documented); there is no scheduler in the code.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | `sources/subscribe` | 2026-11-04 | scanned first (no findings); read in full |
| B-R02 | documentation | `task.md` | 2026-11-04 | the user's own description of the source, not the source's docs |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `sources/subscribe/plans.py:1-2` | renew(subscription, create_order) returns create_order(subscription['customer'], subscription['price']) |
| B-E02 | B-R02 | documented | `task.md#scenario-m` | The user describes Subscribe as monthly subscriptions that create orders |

## Features

### B-F01 Renew a subscription into an order

- **Source application:** Subscribe (B)
- **Evidence:** B-E01, B-E02
- **Description:** Each renewal of a subscription creates an order for the subscription's customer and price
- **Observed behaviour:** renew() calls the injected create_order(customer, price) once per call and returns its result
- **Business logic:** No period or duplicate check: calling renew twice for the same month creates two orders. The monthly schedule is documented by the user but there is no scheduler in the code.
- **Data requirements:** Subscription.customer, Subscription.price
- **Dependencies:** none
- **Integration requirements:** needs an order-creation function from the host app
- **Basis and confidence:** observed, high

## Screens and workflows

None: the source is a library function with no screens, routes or user interface (observed).

## Navigation

None (observed: no routes or menus).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Subscription | none in the code (in-memory dict) | customer (any), price (number) | none | observed | B-E01 |

## API

No HTTP API (observed). Python entry points: `renew(subscription, create_order)`.

## Authentication and authorization

None in the code (observed). No users, roles or permission checks.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| none | - | - | - |

## Architecture and stack

Python (plain function); none (observed). No packages, no manifest, no runtime pin.

## Configuration

None (observed: no settings or environment variables).

## Error handling

- any: no error handling in the code (observed)

## Unknowns

- How and when renew() is triggered monthly: no scheduler in the code (task.md says monthly)
- Unit and currency of subscription['price']
- Whether a subscription has an id, a status or a billing period: none in the code
- Rights: task.md states no rights and there is no licence file, so code_reuse is unknown and nothing is copied
