# Compatibility report

Scope: kept features only. Apps: A, B, C.

| Severity | Count |
|---|---|
| critical | 5 |
| high | 1 |
| medium | 3 |
| info | 1 |

## application:integration:refund-not-idempotent

- **Conflict:** gateway.refund(charge_id) has no idempotency key (gateway.py:23-25): every call creates a new refund, so a retried cancel or a cancel racing a refund webhook could refund twice.
- **Affected applications:** A, C
- **Affected features:** M03, M04
- **Severity:** critical
- **Possible solutions:** Record a refund-requested marker before calling the gateway and never call refund again once it exists; Only refund from webhooks
- **Recommended resolution:** Write a refund marker first; with a marker present, a retry completes the order as refunded without calling the gateway
- **User approval required:** yes
- **Status:** resolved (D05: refund marker written before gateway.refund; with a marker present a retry completes as refunded without a second gateway call)

## application:workflow:cancel-paid-order

- **Conflict:** C cancels a paid order without refunding it (orders.py:3), so money A charged is kept for a cancelled order; the user requires a cancelled paid order to be refunded exactly once.
- **Affected applications:** A, C
- **Affected features:** M02, M04
- **Severity:** critical
- **Possible solutions:** Cancel of a paid order refunds through the gateway and ends in status refunded; Forbid cancelling paid orders
- **Recommended resolution:** pending->cancelled; paid->refund once->refunded; cancelled/refunded->no-op
- **User approval required:** yes
- **Status:** resolved (D02 (user requirement in task.md): pending->cancelled; paid->one gateway refund->status refunded with one ledger refund; cancelled/refunded->no-op)

## application:workflow:charge-retry-idempotency

- **Conflict:** A's idempotency key falls back to str(id(order)) and gateway timeouts are not handled: after a timeout that charged, the order stays unpaid and a retry with another key charges twice.
- **Affected applications:** A
- **Affected features:** M02
- **Severity:** critical
- **Possible solutions:** Require the client key, remember the first key per order and reuse it for every retry; Derive a per-order gateway key
- **Recommended resolution:** Client key required; first attempted key per order is recorded before the gateway call and reused on every retry; a key used for another order is refused; already-paid orders are never charged
- **User approval required:** yes
- **Status:** resolved (D03: client key required; first key per order recorded before the charge and reused for every retry; key reuse across orders refused; paid orders never charged; GatewayTimeout re-raised with order left pending and the attempt recorded so a retry collects the original charge)

## application:workflow:webhook-redelivery

- **Conflict:** A applies every webhook delivery again and ignores the type; a duplicate delivery, or a webhook plus the synchronous pay() result, would be applied (and ledgered) twice.
- **Affected applications:** A
- **Affected features:** M03
- **Severity:** critical
- **Possible solutions:** De-duplicate by event id and make transitions state-checked; Ignore webhooks and rely on pay() only
- **Recommended resolution:** Record processed event ids atomically with the change; charge.succeeded only moves pending->paid, charge.refunded only paid->refunded; the ledger is appended only on a real transition
- **User approval required:** yes
- **Status:** resolved (D04: processed event ids stored atomically with the change; state-checked transitions; ledger appended only on a real transition)

## database:payment-state:order-payment-state

- **Conflict:** A records payment as a boolean 'paid' flag; C records it as status pending/paid/cancelled/refunded. Two sources of truth can disagree (paid=True while status=cancelled).
- **Affected applications:** A, C
- **Affected features:** M01, M02, M03
- **Severity:** critical
- **Possible solutions:** Make Order.status the only payment state and drop A's paid flag; Keep both and sync them
- **Recommended resolution:** Order.status is the single source of truth; 'paid' is derived (status == paid)
- **User approval required:** yes
- **Status:** resolved (D01: Order.status is the single payment state; A's paid flag dropped (derived from status))

## database:persistence:partial-writes

- **Conflict:** No source persists anything; the user requires that a failed store write (StoreError) leaves the order unchanged, and the gateway call cannot be inside the write.
- **Affected applications:** A, B, C
- **Affected features:** M02, M03, M04, M05
- **Severity:** high
- **Possible solutions:** One atomic write per state change, checked before any mutation; intent markers written before gateway calls; Two-phase with compensation
- **Recommended resolution:** Every state change is one atomic store write (all or nothing); payment and refund intents are written before the gateway call so a retry after a failed write is safe
- **User approval required:** yes
- **Status:** resolved (D06: one atomic store write per state change (fail check before any mutation); intent records written before gateway calls)

## application:business-rule:amount-units

- **Conflict:** A uses order['amount'], B subscription['price'], the task uses amount_cents.
- **Affected applications:** A, B
- **Affected features:** M02, M05
- **Severity:** medium
- **Possible solutions:** Integer cents everywhere (amount_cents)
- **Recommended resolution:** amount_cents, positive integer
- **User approval required:** no
- **Status:** resolved (D07: integer amount_cents everywhere (A amount and B price map to it))

## application:workflow:renewal-duplication

- **Conflict:** B creates a new order on every renew() call; renewing one period twice would bill the month twice.
- **Affected applications:** B
- **Affected features:** M05
- **Severity:** medium
- **Possible solutions:** Optional period key de-duplicates renewals; Leave scheduling to the caller
- **Recommended resolution:** renew(subscription, period) returns the existing order for the same subscription id and period
- **User approval required:** no
- **Status:** resolved (D08: renew(subscription, period) de-duplicates by subscription id + period)

## database:duplicate-entity:order

- **Conflict:** Order exists in A:Order, C:Order; fields not shared: amount_cents (only A), charge_id (only A), paid (only A), status (only C)
- **Affected applications:** A, C
- **Affected features:** M01, M02, M03, M04
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (D09: one Order entity merging A (amount_cents, charge_id) and C (status) fields)

## database:unknown-type:order.primary-key

- **Conflict:** Order primary key type is not known for A, C; find it before deciding the merged key
- **Affected applications:** A, C
- **Affected features:** M01, M02, M03, M04
- **Severity:** info
- **Possible solutions:** Read the source's schema or migrations for the type; Record it as unknown and decide in the architecture
- **Recommended resolution:** Find the real type before designing the merged entity
- **User approval required:** no
- **Status:** resolved (D10: Order primary key is a generated string id ord_<n>)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Order | A, C | add fields that only some sources have: amount_cents (only A), charge_id (only A), paid (only A), status (only C) (low); A.Order.amount: number to integer can lose or reject values (high); A.Order.paid: boolean to str: pending|paid|cancelled|refunded can lose or reject values (high) | high | amount, paid | yes |
