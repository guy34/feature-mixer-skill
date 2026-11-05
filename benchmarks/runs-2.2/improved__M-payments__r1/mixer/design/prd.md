# Unified Billing: product requirements

Version: 2026-11-05 · Sources: A: Billfold, B: Subscribe, C: Orderly · Status: approved (benchmark operator, pre-approved)

## Problem

A merchant takes payment for one-off and monthly orders through a payment
gateway. Billfold charges and receives webhooks, Subscribe turns renewals
into orders, Orderly tracks order states, but none of them is safe on its
own: Billfold can charge twice and applies every webhook again (observed),
Orderly cancels a paid order without a refund (observed), and Subscribe can
create two orders for one renewal (observed). The combined module keeps each
source's job and makes money movement exactly-once: never charge twice,
never apply a webhook twice, keep orders consistent when the gateway times
out or a write fails, and refund a cancelled paid order exactly once
(task.md).

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Host application (the merchant's backend) | create orders, take payment, react to gateway webhooks, cancel and refund | calls the Python API in-process; it authenticates its own users |
| Payment gateway | report charges and refunds | sends webhook events the host passes to `handle_webhook` |
| Finance / support | see what money moved | reads `ledger()` and `order()` |

## Core loop

1. `create_order(customer, amount_cents)` gives a pending order.
2. `pay(order_id, key)` charges it once; a retry with the same key is safe.
3. The gateway's `charge.succeeded` webhook confirms it (applied once).
4. `cancel(order_id)` on a paid order refunds it once.
5. `ledger()` shows one charge and one refund.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Charge an order with an idempotency key | A | improve | must | required key, one gateway key per order, timeout retry with the same key |
| M02 | Apply gateway webhooks exactly once | A | improve | must | event-id dedupe in the same write as the effect |
| M03 | Renew a subscription into an order | B | improve | should | one order per subscription per period |
| M04 | Order lifecycle states | C | improve | must | single status, enforced transitions |
| M05 | Cancel an order, refunding it if paid | C | improve | must | refund exactly once, ends `refunded` |
| M06 | Ledger of charges and refunds | new (requested by the user) | rebuild | must | written in the same write as the order change |
| M07 | Create and look up orders | new (requested by the user) | rebuild | must | validated input, integer cents |

## User journeys

**J1 Pay and refund an order:** create order → pay (retry with the same key) → webhook delivered twice → cancel → ledger shows one charge and one refund. Features: M07, M04, M01, M02, M05, M06.

**J2 Monthly renewal:** renew a subscription for a period → pay the order → renew again for the same period returns the same order. Features: M03, M07, M01.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given a pending order, when pay is retried with the same key, or called with a new key after it is paid, then the gateway holds exactly one charge, the order is paid with that charge id and the ledger has one charge. |
| AC02 | M01 | Given the gateway times out after the charge went through, when pay is called (and retried if it raised), then exactly one charge exists and the order ends paid with that charge's id. |
| AC03 | M02 | Given a charge.succeeded or charge.refunded event, when it is delivered more than once, then its effect and its ledger entry are applied once. |
| AC04 | M01, M02, M05, M07 | Given the store's fail_next_write is set, when create_order, pay, handle_webhook or cancel is called, then StoreError is raised, the order is unchanged, the gateway is not called, and a retry then succeeds once. |
| AC05 | M05 | Given a paid order, when it is cancelled (twice), then the gateway records one refund, the order is refunded and the ledger has one refund; a pending order is cancelled without a refund. |
| AC06 | M04 | Given an order, when a move outside the transition table is asked for (pay a cancelled order, pay a refunded order), then it is refused with InvalidTransition and the order is unchanged. |
| AC07 | M03 | Given a subscription, when it is renewed twice for the same period, then one order exists; a new period creates a new order. |
| AC08 | M07 | Given invalid input (empty customer, non-integer, boolean or non-positive amount, unknown order id), when create_order or order is called, then it is rejected and nothing is stored; order() returns status, amount_cents and charge_id. |
| AC09 | M06 | Given charges and refunds, when ledger() is read, then it lists each money movement once, in order, as order_id, kind and amount_cents, and changing the returned list does not change the ledger. |
| AC10 | M01, M02, M05, M06, M07 | Given a new order, when the whole journey J1 runs, then the order ends refunded with one charge and one refund at the gateway and in the ledger. |

## Non-functional requirements

- Python 3.8+, standard library only; no network; no secrets.
- Every state change is one atomic store write; operations are serialised
  by one lock so concurrent calls in one process cannot interleave.
- No personal data in logs (the module does not log).
- Tested only against the mock gateway (`gateway.py`): behaviour against a
  real gateway is not testable here.

## Out of scope

| Item | Why |
| --- | --- |
| Monthly scheduler for renewals | no source has one; the host calls renew() per period |
| HTTP endpoint and signature check for webhooks | not in any source or in task.md; the host receives webhooks and passes the event in |
| Real gateway, real database | mock gateway only (task.md); no installs or network approved |
| Partial refunds, currencies | in no source and not asked for |

## Open questions

- Whether a host wants `cancel` on a paid order to end in `cancelled` rather than `refunded` (D07 chose `refunded`, since the money went back).
- Real gateways can fail a refund; the module then leaves the refund `requested` for reconciliation (D08). Not testable with the mock, which never fails a refund.
