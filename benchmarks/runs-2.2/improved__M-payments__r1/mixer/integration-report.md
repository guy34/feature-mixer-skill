# Unified Billing: integration report

Run `20261105T130401391086Z-067232` by run_tests.py · Command: `python -m unittest discover -s tests -t . (Feature Mixer harness)` · Framework: unittest
Started 2026-11-05T13:04:01+00:00 · Finished 2026-11-05T13:04:01+00:00 · Exit code 0 · Outcome exited · **Verdict: passed**
Evidence: `test-runs/20261105T130401391086Z-067232/output.log` (sha256 6093f89ae364...), `test-runs/20261105T130401391086Z-067232/results.xml` (sha256 e994c2e0fa5d...)

Statuses come from the results file of this run. Run `verify_tests.py` to check this report against the evidence; only verified passes prove a feature.

## Summary

| Total | Passed | Failed | Skipped | Not executed | Unverified |
| --- | --- | --- | --- | --- | --- |
| 26 | 26 | 0 | 0 | 0 | 0 |

| Feature | Tests passed | Status |
| --- | --- | --- |
| M01 | 12 of 12 | passing |
| M02 | 7 of 7 | passing |
| M03 | 2 of 2 | passing |
| M04 | 4 of 4 | passing |
| M05 | 5 of 5 | passing |
| M06 | 4 of 4 | passing |
| M07 | 7 of 7 | passing |

## Results

| Test | Level | Features | Acceptance | Expected | Actual | Status |
| --- | --- | --- | --- | --- | --- | --- |
| tests.test_billing.V1CoreLoop.test_create_and_read_order | unit | M07, M04 | AC08 | a new order is pending with its amount and no charge | as expected | passed |
| tests.test_billing.V1CoreLoop.test_create_order_validates_input | unit | M07 | AC08 | bad customer or amount and unknown ids are rejected and nothing is stored | as expected | passed |
| tests.test_billing.V1CoreLoop.test_default_store_and_store_flag | database | M07, M01 | AC04 | without a store the app makes its own, whose fail_next_write works the same | as expected | passed |
| tests.test_billing.V1CoreLoop.test_failed_commit_after_charge_is_recovered_without_second_charge | database | M01 | AC04 | when the write after the charge fails, the order stays pending and the retry reuses the charge | as expected | passed |
| tests.test_billing.V1CoreLoop.test_failed_write_on_create_creates_nothing | database | M07 | AC04 | StoreError and no order | as expected | passed |
| tests.test_billing.V1CoreLoop.test_failed_write_on_pay_leaves_order_unchanged | database | M01 | AC04 | StoreError, order unchanged, gateway not called; the retry charges once | as expected | passed |
| tests.test_billing.V1CoreLoop.test_invalid_transitions_are_refused | unit | M04 | AC06 | cancelled and refunded orders cannot be paid; nothing is charged | as expected | passed |
| tests.test_billing.V1CoreLoop.test_key_is_required_and_bound_to_one_order | unit | M01 | AC01 | no key is refused; a key used for one order cannot pay another | as expected | passed |
| tests.test_billing.V1CoreLoop.test_ledger_is_a_copy_in_order | unit | M06 | AC09 | entries in order, one per money movement; editing the result changes nothing | as expected | passed |
| tests.test_billing.V1CoreLoop.test_paid_order_with_new_key_is_not_charged_again | unit | M01 | AC01 | a paid order is never charged again, whatever key is sent | as expected | passed |
| tests.test_billing.V1CoreLoop.test_pay_marks_order_paid | unit | M01, M06 | AC01 | one charge, order paid with the gateway's charge id, one ledger charge | as expected | passed |
| tests.test_billing.V1CoreLoop.test_retry_with_same_key_charges_once | unit | M01 | AC01 | paying again with the same key makes no second charge | as expected | passed |
| tests.test_billing.V1CoreLoop.test_timeout_after_success_charges_once_and_order_is_paid | interaction | M01 | AC02 | a lost response is recovered with the same key: one charge, order paid with its id | as expected | passed |
| tests.test_billing.V1CoreLoop.test_timeout_then_retry_with_new_key_still_charges_once | interaction | M01 | AC02 | if the outcome stays unknown, a retry with any key reuses the first key | as expected | passed |
| tests.test_billing.V2Webhooks.test_failed_write_on_webhook_leaves_order_unchanged | database | M02 | AC04 | StoreError, order unchanged and event not recorded; redelivery applies it once | as expected | passed |
| tests.test_billing.V2Webhooks.test_late_charge_on_cancelled_order_is_refunded_once | interaction | M02, M05 | AC03, AC05 | money arriving for a cancelled order is refunded once | as expected | passed |
| tests.test_billing.V2Webhooks.test_redelivered_webhook_is_applied_once | unit | M02 | AC03 | charge.succeeded delivered three times pays once with one ledger charge | as expected | passed |
| tests.test_billing.V2Webhooks.test_refund_webhook_applied_once | unit | M02 | AC03 | charge.refunded delivered twice gives one refund entry and status refunded | as expected | passed |
| tests.test_billing.V2Webhooks.test_unknown_events_are_ignored | unit | M02 | AC03 | unknown types and unknown orders change nothing; a refund event never pays | as expected | passed |
| tests.test_billing.V2Webhooks.test_webhook_after_pay_adds_nothing | interaction | M02, M01 | AC03 | the gateway's confirmation of a charge the app recorded changes nothing | as expected | passed |
| tests.test_billing.V3Cancel.test_cancel_paid_order_refunds_exactly_once | unit | M05 | AC05 | one gateway refund, status refunded, one ledger refund, even when cancelled twice | as expected | passed |
| tests.test_billing.V3Cancel.test_cancel_pending_order | unit | M05, M04 | AC05 | a pending order is cancelled with no refund; cancelling again changes nothing | as expected | passed |
| tests.test_billing.V3Cancel.test_failed_write_on_cancel_leaves_order_unchanged | database | M05 | AC04 | StoreError, order still paid, no refund sent; the retry refunds once | as expected | passed |
| tests.test_billing.V3Cancel.test_journey_pay_webhook_cancel_ledger | journey | M07, M04, M01, M02, M05, M06 | AC10 | create, pay with a retry after a timeout, duplicate webhook, cancel twice: one charge and one refund everywhere | as expected | passed |
| tests.test_billing.V4Renewals.test_journey_renewal_then_payment | journey | M03, M07, M01, M06 | AC07 | a renewal's order is paid once even if the renewal and the payment are retried | as expected | passed |
| tests.test_billing.V4Renewals.test_renewing_same_period_creates_one_order | unit | M03, M07 | AC07 | one order per subscription per period; a new period creates a new order | as expected | passed |

## Failures and fixes

None in this run.

## Not testable here

- A real payment gateway: every test uses the mock `gateway.FakeGateway` (task.md). Real idempotency-key semantics, declines, refund failures and webhook signatures were not tested; external_api is not-needed/unavailable in this session.
- A refund whose gateway outcome is unknown (D08): the mock's refund never fails, so the `RefundPending` path is untested.
- A real database or a store with its own write method: only `MemoryStore` and an object carrying `fail_next_write` were tested.
- Concurrency across processes: the lock only serialises calls within one process.

(Added by Claude after the run; the results above are unchanged. A `verify_tests.py --rerun` under approval A01 reproduced 26/26 passed in run 20261105T130431319163Z-e1909c.)
