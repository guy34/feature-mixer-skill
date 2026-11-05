# Compatibility report

Scope: kept features only. Apps: A, B, C.

| Severity | Count |
|---|---|
| critical | 1 |
| high | 5 |
| medium | 3 |
| info | 1 |

## application:business-rule:charge-idempotency

- **Conflict:** A falls back to str(id(order)) as the idempotency key (not stable across retries or processes) and never checks whether the order is already paid, so a retry or a second pay with a new key charges the customer again. The user requires: never charge twice.
- **Affected applications:** A
- **Affected features:** M01
- **Severity:** critical
- **Possible solutions:** Require the client's key, bind it to one order, record the first attempt's key before calling the gateway and reuse it on every retry, and never charge an order that is already paid; Keep A's behaviour (rejected: breaks the user's requirement)
- **Recommended resolution:** Require the key; one gateway key per order, recorded before the call; no charge for a paid order
- **User approval required:** yes
- **Status:** resolved (The client's key is required (no str(id(order)) fallback) and bound to one order; the first attempt's key is written before the gateway is called and reused on every retry, so one order makes at most one gateway charge; an already-paid order is never charged again whatever key is sent)

## application:business-rule:gateway-timeout

- **Conflict:** In A a gateway exception after the charge went through propagates and the order stays unpaid with no charge id, while the customer has been charged (the mock gateway's timeout_after_success does exactly this).
- **Affected applications:** A
- **Affected features:** M01
- **Severity:** high
- **Possible solutions:** Retry once with the same key (the gateway is idempotent by key); if the outcome is still unknown leave the order pending with its attempt key so the next pay or the charge.succeeded webhook completes it; Mark the order paid on timeout (rejected: no charge id, may not have been charged)
- **Recommended resolution:** Retry with the same key, otherwise stay pending and let the next attempt or the webhook reconcile
- **User approval required:** yes
- **Status:** resolved (On a gateway timeout, retry once with the same key (the gateway is idempotent by key); if the outcome is still unknown the order stays pending with its attempt key and the error is raised; the next pay (any key) or the charge.succeeded webhook completes it without a second charge)

## application:business-rule:webhook-idempotency

- **Conflict:** A applies every webhook delivery again and ignores the event type, so a redelivered or refund event marks the order paid again. The user requires: never apply a webhook twice.
- **Affected applications:** A
- **Affected features:** M02
- **Severity:** high
- **Possible solutions:** Deduplicate by event id inside the same atomic write as the event's effect, and act by event type; Deduplicate by (order, type) only (rejected: a later legitimate event of the same type would be lost)
- **Recommended resolution:** Event-id dedupe in the same write as the effect; type-aware handling; no backwards moves
- **User approval required:** yes
- **Status:** resolved (Each event id is recorded in the same atomic write as its effect; a redelivered event does nothing; charge.succeeded and charge.refunded are handled by type; unknown types and orders are ignored; no backwards moves)

## application:workflow:cancel-paid-order

- **Conflict:** C cancels a paid order without refunding it (its own comment says so) and lets a cancelled or refunded order be cancelled again. The user requires: cancelling a paid order refunds it, exactly once.
- **Affected applications:** A, C
- **Affected features:** M01, M05
- **Severity:** high
- **Possible solutions:** Cancel of a paid order refunds its charge once through the gateway and ends in 'refunded'; cancel is a no-op on cancelled or refunded orders; Keep C's behaviour (rejected by the user's requirement)
- **Recommended resolution:** Refund once and end in 'refunded'; idempotent cancel
- **User approval required:** yes
- **Status:** resolved (Cancelling a pending order ends in 'cancelled'; cancelling a paid order refunds its charge through the gateway exactly once and ends in 'refunded' with one ledger refund; cancelling a cancelled or refunded order is a no-op)

## database:atomicity:write-failure

- **Conflict:** No source persists anything or handles a failed write; the user requires that when a database write fails the order is left unchanged (StoreError) and the order stays consistent. A change spread over several writes, or a gateway call made before the record of it, could leave a charge or refund with no record.
- **Affected applications:** A, B, C
- **Affected features:** M01, M02, M03, M05
- **Severity:** high
- **Possible solutions:** Every state change is one atomic write (order, ledger entry and processed event id together); before calling the gateway, write the intent (attempt key or refund intent) so a failed write means the gateway is never called; Call the gateway first, then write (rejected: a failed write would leave money moved with no record)
- **Recommended resolution:** One atomic write per state change; intent written before any gateway call
- **User approval required:** yes
- **Status:** resolved (Every state change is one atomic store write (order, ledger entry, processed event id together); before any gateway call the intent (attempt key or refund intent) is written first, so when that write fails (StoreError) nothing is changed and the gateway is not called)

## database:field-meaning:order-payment-state

- **Conflict:** A records payment as a boolean 'paid'; C records it as status 'paid' among four states. Two fields for one fact can disagree (A's webhook sets paid=true on a refund event; C's cancel leaves paid=true on a cancelled order).
- **Affected applications:** A, C
- **Affected features:** M01, M02, M04, M05
- **Severity:** high
- **Possible solutions:** One status field with C's four values and a transition table; A's paid becomes status == 'paid'; Keep both fields in sync (rejected: two sources of truth)
- **Recommended resolution:** Single status field; paid is derived, not stored
- **User approval required:** yes
- **Status:** resolved (One status field with C's four values (pending, paid, cancelled, refunded) and an enforced transition table; A's paid flag is not stored (paid means status == 'paid'))

## application:business-rule:renewal-duplicates

- **Conflict:** B creates a new order on every renew() call with no billing period, so a repeated renewal creates a second order, which would then be charged.
- **Affected applications:** B
- **Affected features:** M03
- **Severity:** medium
- **Possible solutions:** One order per subscription per period: a repeated renewal returns the existing order; Keep B's behaviour
- **Recommended resolution:** One order per subscription per period
- **User approval required:** no
- **Status:** resolved (One order per subscription id per period: renewing again for the same period returns the existing order)

## database:duplicate-entity:order

- **Conflict:** Order exists in A:Order, C:Order; fields not shared: amount (only A), charge_id (only A), paid (only A), status (only C)
- **Affected applications:** A, C
- **Affected features:** M01, M02, M04, M05
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge only once it is confirmed they mean the same thing; then list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge A:Order and C:Order into one Order (the user's task.md describes one order flowing from subscription to payment to cancellation); fields: id, customer, amount_cents (from A:Order.amount), status (from C:Order.status, replaces A:Order.paid), charge_id (from A), attempt_key, refund_state, refund_id)

## database:field-meaning:amount-units

- **Conflict:** A's order['amount'] and B's subscription['price'] have no stated unit; the mock gateway takes amount_cents and the user's API uses amount_cents.
- **Affected applications:** A, B
- **Affected features:** M01, M03
- **Severity:** medium
- **Possible solutions:** Integer minor units (amount_cents) everywhere; reject non-integer or non-positive amounts; Decimal major units
- **Recommended resolution:** Integer cents, validated on input
- **User approval required:** no
- **Status:** resolved (Integer minor units: amount_cents on orders, price_cents on subscriptions; non-integer, boolean or non-positive amounts are rejected)

## database:unknown-type:order.primary-key

- **Conflict:** Order primary key type is not known for A, C; find it before deciding the merged key
- **Affected applications:** A, C
- **Affected features:** M01, M02, M04, M05
- **Severity:** info
- **Possible solutions:** Read the source's schema or migrations for the type; Record it as unknown and decide in the architecture
- **Recommended resolution:** Find the real type before designing the merged entity
- **User approval required:** no
- **Status:** resolved (Neither source has a key (in-memory dicts); the unified Order key is a string 'ord_<n>' generated by the app)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Order | A, C | add fields that only some sources have: amount (only A), charge_id (only A), paid (only A), status (only C) (low); A.Order.amount: number to integer can lose or reject values (high); A.Order.paid: boolean to text keeps every value (low) | high | amount | yes |
| Renewal | B | B.Subscription.customer: any to text can lose or reject values (high); B.Subscription.price: number to integer can lose or reject values (high) | high | customer, price | yes |
