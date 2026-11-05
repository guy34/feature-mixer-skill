# Unified Billing: product requirements

Version: 2026-11-05 · Sources: A Billfold, B Subscribe, C Orderly · Status: approved (benchmark operator, pre-approved)

## Problem

Billfold charges and takes webhooks, Subscribe creates orders from subscriptions, Orderly tracks order
states. Separately they can charge twice (unstable key, unhandled timeouts), apply a webhook twice, and
keep money for a cancelled order. One module must give orders, payments, webhooks, cancellation and
renewals with these guarantees: never charge twice, never apply a webhook twice, keep orders consistent
when the gateway times out or a store write fails, and refund a cancelled paid order exactly once.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Server code of a shop or SaaS | take payments safely | caller of the Python API |
| Gateway (mock) | deliver charge events | webhook sender |

## Core loop

create_order -> pay(order_id, key) (retries safe) -> webhook confirms -> order()/ledger() show the truth -> cancel refunds if paid.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Order status lifecycle | C | improve | must | transition table |
| M02 | Charge an order through the gateway | A | improve | must | idempotent, timeout-safe |
| M03 | Apply gateway webhooks | A | improve | must | exactly once |
| M04 | Cancel an order (refund if paid) | C | improve | must | refund exactly once |
| M05 | Renew a subscription into an order | B | improve | must | one order per period |

## User journeys

**J1 Pay:** create_order -> pay -> (timeout -> retry same key) -> paid. Features: M01, M02.
**J2 Confirm:** pay -> charge.succeeded webhook (possibly delivered twice) -> still one ledger charge. Features: M02, M03.
**J3 Cancel:** paid order -> cancel (possibly twice, possibly with a failed write) -> one refund. Features: M04.
**J4 Renew:** renew(subscription, period) -> order -> pay. Features: M05, M02.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given create_order(c, 500), then order() is pending, 500, charge_id None; non-positive or non-integer amounts are refused. |
| AC02 | M02 | Given a pending order, when pay is called twice with the same key, then the gateway has one charge and the ledger one charge entry. |
| AC03 | M02 | Given the gateway times out after charging, when pay raises and is retried with the same key (or another key), then there is still one charge and the order is paid. |
| AC04 | M02 | Given fail_next_write, when pay is called, then StoreError is raised and the order is unchanged; a retry pays once. |
| AC05 | M03 | Given a charge.succeeded event delivered twice, then the order is paid once and the ledger has one charge. |
| AC06 | M03 | Given pay already succeeded, when charge.succeeded arrives, then nothing is added to the ledger. |
| AC07 | M03 | Given fail_next_write, when a webhook is handled, then StoreError is raised, the order is unchanged and a redelivery applies once. |
| AC08 | M04 | Given a paid order, when cancel is called (twice), then one gateway refund, status refunded, one ledger refund. |
| AC09 | M04 | Given a pending order, when cancel is called, then status cancelled and no refund. |
| AC10 | M04 | Given fail_next_write during cancel of a paid order, then StoreError, the order is unchanged, and a retry refunds exactly once. |
| AC11 | M05 | Given a subscription, when renew is called twice for one period, then one order exists. |

## Non-functional requirements

Standard library only; thread-safe through one lock; no secrets; mock gateway only.

## Out of scope

| Item | Why |
| --- | --- |
| Real payment gateway, webhook signature verification | the user asked for a mock gateway only |
| HTTP layer, persistence to a database | not requested; Store is replaceable |
| Renewal scheduler | not in any source; caller schedules renewals |

## Open questions

- Final status after cancelling a paid order is "refunded" (Claude's choice; task.md does not name it).
