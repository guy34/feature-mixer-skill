# Unified Billing (Scenario M: billing, subscriptions and orders): integration report

Run `20261105T130725609331Z` by run_tests.py · Command: `python -m unittest discover -s tests -t . (Feature Mixer harness)` · Framework: unittest
Started 2026-11-05T13:07:25+00:00 · Finished 2026-11-05T13:07:25+00:00 · Exit code 0
Evidence: `test-runs/20261105T130725609331Z/output.log` (sha256 9c6dccdc7faf...), `test-runs/20261105T130725609331Z/results.xml` (sha256 494e21cabb2a...)

Statuses come from the results file of this run. Run `verify_tests.py` to check this report against the evidence; only verified passes prove a feature.

## Summary

| Total | Passed | Failed | Skipped | Not executed | Unverified |
| --- | --- | --- | --- | --- | --- |
| 31 | 31 | 0 | 0 | 0 | 0 |

| Feature | Tests passed | Status |
| --- | --- | --- |
| M01 | 12 of 12 | passing |
| M02 | 16 of 16 | passing |
| M03 | 10 of 10 | passing |
| M04 | 7 of 7 | passing |
| M05 | 3 of 3 | passing |

## Results

| Test | Level | Features | Acceptance | Expected | Actual | Status |
| --- | --- | --- | --- | --- | --- | --- |
| tests.test_v1_orders_payments.OrdersTest.test_create_order_is_pending | unit | M01 | AC01 | a new order is pending with its amount and no charge | as expected | passed |
| tests.test_v1_orders_payments.OrdersTest.test_create_order_write_failure_creates_nothing | database | M01 | AC01 | a failed write raises StoreError and no order exists afterwards | as expected | passed |
| tests.test_v1_orders_payments.OrdersTest.test_invalid_amounts_and_missing_order | unit | M01 | AC01 | non-positive, non-integer and bool amounts are refused; unknown ids raise OrderNotFound | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_default_store_exposed | unit | M01 | AC04 | create_app without a store exposes app.store with fail_next_write False | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_foreign_store_object_controls_failures | database | M02, M01 | AC04 | any object with fail_next_write works as the store; its flag makes the next write fail once | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_key_reused_for_other_order_refused | unit | M02 | AC02 | a key already used for order 1 is refused for order 2, which stays pending and uncharged | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_missing_key_refused | unit | M02 | AC02 | pay without an idempotency key is refused before any charge | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_paid_order_with_new_key_not_charged | unit | M02 | AC02 | paying an already paid order with a different key does not charge again | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_pay_marks_paid_and_ledgers_once | unit | M02, M01 | AC02 | paying charges the gateway once, order paid with the charge id, one ledger charge | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_retry_same_key_never_charges_twice | unit | M02 | AC02 | three pays with the same key give one gateway charge and one ledger entry | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_timeout_exception_importable_from_module | unit | M02 | AC03 | billing re-exports the gateway's GatewayTimeout | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_timeout_then_retry_other_key_charges_once | interaction | M02 | AC03 | after a timeout, a retry with a new key reuses the first gateway key, so no second charge | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_timeout_then_retry_same_key_charges_once | interaction | M02, M01 | AC03 | a timeout after a successful charge leaves the order pending; the retry gets the same charge | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_write_failure_after_charge_retry_collects_same_charge | database | M02 | AC04 | if the write after a successful charge fails, the order stays pending and a retry with any key does not charge again | as expected | passed |
| tests.test_v1_orders_payments.PaymentsTest.test_write_failure_during_pay_leaves_order_unchanged | database | M02, M01 | AC04 | StoreError, order unchanged and no ledger entry; the retry charges exactly once | as expected | passed |
| tests.test_v2_webhooks.WebhookTest.test_duplicate_delivery_applied_once | unit | M03 | AC05 | the same event delivered three times is applied once | as expected | passed |
| tests.test_v2_webhooks.WebhookTest.test_ignored_events | unit | M03 | AC05 | unknown orders, unknown types, wrong charge ids and refunds of pending orders change nothing | as expected | passed |
| tests.test_v2_webhooks.WebhookTest.test_refunded_webhook_refunds_paid_order_once | unit | M03, M01 | AC05 | charge.refunded moves a paid order to refunded with one ledger refund; redelivery does nothing | as expected | passed |
| tests.test_v2_webhooks.WebhookTest.test_succeeded_webhook_marks_pending_order_paid | unit | M03, M01 | AC05 | charge.succeeded moves a pending order to paid with the event's charge id and one ledger charge | as expected | passed |
| tests.test_v2_webhooks.WebhookTest.test_webhook_after_pay_adds_nothing | interaction | M03, M02 | AC06 | pay then charge.succeeded for the same charge leaves one ledger charge; pay again does not charge | as expected | passed |
| tests.test_v2_webhooks.WebhookTest.test_webhook_after_timeout_then_retry | interaction | M03, M02 | AC06 | timeout, then the webhook confirms the charge, then the client retry neither charges nor ledgers again | as expected | passed |
| tests.test_v2_webhooks.WebhookTest.test_write_failure_leaves_order_unchanged_and_redelivery_applies | database | M03 | AC07 | StoreError while applying an event leaves the order pending; the redelivered event applies once | as expected | passed |
| tests.test_v3_cancel.CancelTest.test_cancel_paid_refunds_exactly_once | interaction | M04, M02 | AC08 | cancelling a paid order twice refunds once, status refunded, ledger charge then refund | as expected | passed |
| tests.test_v3_cancel.CancelTest.test_cancel_pending_no_refund | unit | M04, M01 | AC09 | a pending order becomes cancelled, no gateway refund, no ledger entry, cannot be paid after | as expected | passed |
| tests.test_v3_cancel.CancelTest.test_cancel_then_refund_webhook_not_applied_twice | interaction | M04, M03 | AC08 | the gateway's charge.refunded webhook after a cancel adds no second refund | as expected | passed |
| tests.test_v3_cancel.CancelTest.test_late_charge_on_cancelled_order_is_refunded_once | interaction | M04, M03, M02 | AC08 | pay times out, the order is cancelled, then charge.succeeded arrives: the charge is refunded once | as expected | passed |
| tests.test_v3_cancel.CancelTest.test_write_failure_after_refund_never_refunds_again | database | M04 | AC10 | if the write after the gateway refund fails, the order stays paid and a retry completes without a second refund | as expected | passed |
| tests.test_v3_cancel.CancelTest.test_write_failure_before_refund | database | M04 | AC10 | StoreError on cancel leaves the paid order unchanged; the retry refunds exactly once | as expected | passed |
| tests.test_v4_renewals.RenewalTest.test_renew_creates_order | unit | M05, M01 | AC11 | a renewal creates a pending order for the customer at the subscription price | as expected | passed |
| tests.test_v4_renewals.RenewalTest.test_renewal_journey_pay_and_cancel | journey | M05, M02, M04, M03 | AC11 | renewal order is paid once with retries, confirmed by webhook, and refunded once on cancel | as expected | passed |
| tests.test_v4_renewals.RenewalTest.test_same_period_renewed_once | unit | M05 | AC11 | renewing the same period twice returns the same order; a new period makes a new order | as expected | passed |

## Failures and fixes

None in this run.

## Not testable here

Nothing recorded.

## Not testable here

- A real payment gateway, real webhook delivery and webhook signature verification: the task allows the mock gateway only.
- Durable persistence and process crashes: the Store is in-memory; crash safety is reasoned from the write order (intent records before gateway calls), not tested against a real database.
- Concurrency under real threads: operations are serialised by one lock; no multi-threaded stress test was run.
- A refund whose gateway call times out is completed as refunded on retry without a second gateway call (D05); FakeGateway.refund never times out, so that path is untested.
