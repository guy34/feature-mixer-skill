# Scenario M: billing, subscriptions and orders

- **A (Billfold)**, `sources/billfold`: charges cards through a payment gateway and receives its webhooks.
- **B (Subscribe)**, `sources/subscribe`: monthly subscriptions that create orders.
- **C (Orderly)**, `sources/orderly`: orders with states pending, paid, cancelled, refunded.

Use a **mock** gateway only (`gateway.py` in this folder, the same one the hidden tests use). The unified app
must never charge twice, never apply a webhook twice, keep every order in a consistent state when the gateway
times out or a database write fails, and refund a paid order that is cancelled exactly once.

Build `unified/billing.py`:

```python
app = create_app(gateway, store=None)      # gateway: gateway.FakeGateway(); store: optional, see below
order_id = app.create_order(customer, amount_cents)
app.pay(order_id, key)          # key: the client's idempotency key; retrying with the same key never charges twice
app.handle_webhook(event)       # {"id", "type": "charge.succeeded" | "charge.refunded", "order_id", "charge_id"}
app.cancel(order_id)            # cancelling a paid order refunds it
app.order(order_id) -> {"status", "amount_cents", "charge_id"}
app.ledger() -> list of {"order_id", "kind": "charge" | "refund", "amount_cents"}
```
`store` is an object with `fail_next_write = False`; when the test sets it to True, the next write the app
makes must fail (raise `StoreError`, importable from the module) and leave the order unchanged.
