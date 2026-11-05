# Unified Billing

`unified/billing.py`: orders, idempotent payments, exactly-once webhooks,
cancel with refund, a money ledger and subscription renewals, built by
Feature Mixer from Billfold (A), Subscribe (B) and Orderly (C). Python 3.8+,
standard library only. Design: `../mixer/design/architecture.md`.

Run the tests from this folder (they load the mock gateway from `../gateway.py`):

    python3 -m unittest discover -s tests -t .

Only the mock gateway is supported here; a real gateway needs an adapter with
the same `charge(amount_cents, key)` / `refund(charge_id)` interface and has
not been tested.
