"""Tests for unified/billing.py, tagged with menu features and acceptance criteria."""

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
sys.path.insert(0, APP)

from unified import billing  # noqa: E402
from unified.billing import (  # noqa: E402
    IdempotencyConflict, InvalidRequest, InvalidTransition, StoreError, UnknownOrder, create_app)


def _load_gateway():
    path = os.path.join(os.path.dirname(APP), "gateway.py")
    spec = importlib.util.spec_from_file_location("gateway", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gateway = _load_gateway()


class StoreStub:
    """The store shape task.md describes: an object with fail_next_write."""
    fail_next_write = False


class Base(unittest.TestCase):
    def setUp(self):
        self.gw = gateway.FakeGateway()
        self.store = StoreStub()
        self.app = create_app(self.gw, store=self.store)

    def paid_order(self, amount=1500, key="k-paid"):
        oid = self.app.create_order("alice", amount)
        self.app.pay(oid, key)
        return oid


class V1CoreLoop(Base):
    def test_create_and_read_order(self):
        """features: M07, M04
        acceptance: AC08
        expect: a new order is pending with its amount and no charge
        level: unit"""
        oid = self.app.create_order("alice", 1200)
        self.assertEqual(self.app.order(oid), {"status": "pending", "amount_cents": 1200, "charge_id": None})

    def test_create_order_validates_input(self):
        """features: M07
        acceptance: AC08
        expect: bad customer or amount and unknown ids are rejected and nothing is stored
        level: unit"""
        for customer, amount in (("", 100), (None, 100), ("bob", 0), ("bob", -5), ("bob", 10.5),
                                 ("bob", True), ("bob", "100")):
            with self.assertRaises(InvalidRequest):
                self.app.create_order(customer, amount)
        self.assertEqual(self.app.ledger(), [])
        with self.assertRaises(UnknownOrder):
            self.app.order("ord_404")
        with self.assertRaises(KeyError):
            self.app.order("nope")

    def test_pay_marks_order_paid(self):
        """features: M01, M06
        acceptance: AC01
        expect: one charge, order paid with the gateway's charge id, one ledger charge
        level: unit"""
        oid = self.app.create_order("alice", 1500)
        cid = self.app.pay(oid, "k1")
        self.assertEqual(self.app.order(oid), {"status": "paid", "amount_cents": 1500, "charge_id": cid})
        self.assertEqual(self.gw.charges, {cid: 1500})
        self.assertEqual(self.app.ledger(), [{"order_id": oid, "kind": "charge", "amount_cents": 1500}])

    def test_retry_with_same_key_charges_once(self):
        """features: M01
        acceptance: AC01
        expect: paying again with the same key makes no second charge
        level: unit"""
        oid = self.app.create_order("alice", 1500)
        first = self.app.pay(oid, "k1")
        second = self.app.pay(oid, "k1")
        self.assertEqual(first, second)
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(len(self.app.ledger()), 1)

    def test_paid_order_with_new_key_is_not_charged_again(self):
        """features: M01
        acceptance: AC01
        expect: a paid order is never charged again, whatever key is sent
        level: unit"""
        oid = self.paid_order(key="k1")
        self.app.pay(oid, "k2")
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(len(self.app.ledger()), 1)

    def test_key_is_required_and_bound_to_one_order(self):
        """features: M01
        acceptance: AC01
        expect: no key is refused; a key used for one order cannot pay another
        level: unit"""
        a = self.app.create_order("alice", 100)
        b = self.app.create_order("bob", 200)
        for bad in (None, ""):
            with self.assertRaises(InvalidRequest):
                self.app.pay(a, bad)
        self.app.pay(a, "shared")
        with self.assertRaises(IdempotencyConflict):
            self.app.pay(b, "shared")
        self.assertEqual(self.app.order(b)["status"], "pending")
        self.assertEqual(len(self.gw.charges), 1)

    def test_timeout_after_success_charges_once_and_order_is_paid(self):
        """features: M01
        acceptance: AC02
        expect: a lost response is recovered with the same key: one charge, order paid with its id
        level: interaction"""
        oid = self.app.create_order("alice", 900)
        self.gw.timeout_after_success = True
        try:
            self.app.pay(oid, "k1")
        except gateway.GatewayTimeout:
            pass
        self.app.pay(oid, "k1")
        self.assertEqual(len(self.gw.charges), 1)
        (cid,) = self.gw.charges
        self.assertEqual(self.app.order(oid), {"status": "paid", "amount_cents": 900, "charge_id": cid})
        self.assertEqual(len(self.app.ledger()), 1)

    def test_timeout_then_retry_with_new_key_still_charges_once(self):
        """features: M01
        acceptance: AC02
        expect: if the outcome stays unknown, a retry with any key reuses the first key
        level: interaction"""

        class AlwaysTimesOut:
            def __init__(self, inner):
                self.inner, self.calls = inner, 0

            def charge(self, amount, key):
                self.calls += 1
                self.inner.charge(amount, key)
                raise gateway.GatewayTimeout("lost")

            def refund(self, charge_id):
                return self.inner.refund(charge_id)

        flaky = AlwaysTimesOut(self.gw)
        app = create_app(flaky)
        oid = app.create_order("alice", 700)
        with self.assertRaises(gateway.GatewayTimeout):
            app.pay(oid, "k1")
        self.assertEqual(app.order(oid)["status"], "pending")
        app._gw.gateway = self.gw  # the gateway recovers
        app.pay(oid, "k2")
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(app.order(oid)["status"], "paid")

    def test_failed_write_on_pay_leaves_order_unchanged(self):
        """features: M01
        acceptance: AC04
        expect: StoreError, order unchanged, gateway not called; the retry charges once
        level: database"""
        oid = self.app.create_order("alice", 1500)
        self.store.fail_next_write = True
        with self.assertRaises(StoreError):
            self.app.pay(oid, "k1")
        self.assertEqual(self.app.order(oid), {"status": "pending", "amount_cents": 1500, "charge_id": None})
        self.assertEqual(self.gw.charges, {})
        self.assertFalse(self.store.fail_next_write)
        self.app.pay(oid, "k1")
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(self.app.order(oid)["status"], "paid")

    def test_failed_commit_after_charge_is_recovered_without_second_charge(self):
        """features: M01
        acceptance: AC04
        expect: when the write after the charge fails, the order stays pending and the retry reuses the charge
        level: database"""
        oid = self.app.create_order("alice", 1500)
        self.app._store.write([("key", "warm", oid)])  # bind the key so the next write is the commit
        record = dict(self.app._store.orders[oid], attempt_key="warm")
        self.app._store.write([("order", record)])
        self.store.fail_next_write = True
        with self.assertRaises(StoreError):
            self.app.pay(oid, "warm")
        self.assertEqual(self.app.order(oid)["status"], "pending")
        self.assertEqual(len(self.gw.charges), 1)
        self.app.pay(oid, "another-key")
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(self.app.order(oid)["status"], "paid")
        self.assertEqual(len(self.app.ledger()), 1)

    def test_failed_write_on_create_creates_nothing(self):
        """features: M07
        acceptance: AC04
        expect: StoreError and no order
        level: database"""
        self.store.fail_next_write = True
        with self.assertRaises(StoreError):
            self.app.create_order("alice", 100)
        oid = self.app.create_order("alice", 100)
        self.assertEqual(oid, "ord_1")

    def test_default_store_and_store_flag(self):
        """features: M07, M01
        acceptance: AC04
        expect: without a store the app makes its own, whose fail_next_write works the same
        level: database"""
        app = create_app(self.gw)
        oid = app.create_order("alice", 100)
        app.store.fail_next_write = True
        with self.assertRaises(billing.StoreError):
            app.pay(oid, "k")
        self.assertEqual(app.order(oid)["status"], "pending")
        app.pay(oid, "k")
        self.assertEqual(app.order(oid)["status"], "paid")

    def test_invalid_transitions_are_refused(self):
        """features: M04
        acceptance: AC06
        expect: cancelled and refunded orders cannot be paid; nothing is charged
        level: unit"""
        cancelled = self.app.create_order("alice", 100)
        self.app.cancel(cancelled)
        with self.assertRaises(InvalidTransition):
            self.app.pay(cancelled, "k1")
        refunded = self.paid_order(key="k2")
        self.app.cancel(refunded)
        with self.assertRaises(InvalidTransition):
            self.app.pay(refunded, "k3")
        self.assertEqual(self.app.order(cancelled)["status"], "cancelled")
        self.assertEqual(self.app.order(refunded)["status"], "refunded")
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(set(billing.STATES), {"pending", "paid", "cancelled", "refunded"})

    def test_ledger_is_a_copy_in_order(self):
        """features: M06
        acceptance: AC09
        expect: entries in order, one per money movement; editing the result changes nothing
        level: unit"""
        a = self.paid_order(amount=100, key="a")
        b = self.paid_order(amount=250, key="b")
        self.app.cancel(a)
        expected = [{"order_id": a, "kind": "charge", "amount_cents": 100},
                    {"order_id": b, "kind": "charge", "amount_cents": 250},
                    {"order_id": a, "kind": "refund", "amount_cents": 100}]
        got = self.app.ledger()
        self.assertEqual(got, expected)
        got.clear()
        self.assertEqual(self.app.ledger(), expected)


class V2Webhooks(Base):
    def event(self, eid, kind, oid, cid):
        return {"id": eid, "type": kind, "order_id": oid, "charge_id": cid}

    def test_redelivered_webhook_is_applied_once(self):
        """features: M02
        acceptance: AC03
        expect: charge.succeeded delivered three times pays once with one ledger charge
        level: unit"""
        oid = self.app.create_order("alice", 500)
        ev = self.event("evt_1", "charge.succeeded", oid, "ch_9")
        for _ in range(3):
            self.app.handle_webhook(dict(ev))
        self.assertEqual(self.app.order(oid), {"status": "paid", "amount_cents": 500, "charge_id": "ch_9"})
        self.assertEqual(len(self.app.ledger()), 1)

    def test_webhook_after_pay_adds_nothing(self):
        """features: M02, M01
        acceptance: AC03
        expect: the gateway's confirmation of a charge the app recorded changes nothing
        level: interaction"""
        oid = self.paid_order(amount=500, key="k1")
        cid = self.app.order(oid)["charge_id"]
        self.app.handle_webhook(self.event("evt_1", "charge.succeeded", oid, cid))
        self.app.handle_webhook(self.event("evt_2", "charge.succeeded", oid, cid))
        self.assertEqual(self.app.order(oid)["status"], "paid")
        self.assertEqual(len(self.app.ledger()), 1)

    def test_refund_webhook_applied_once(self):
        """features: M02
        acceptance: AC03
        expect: charge.refunded delivered twice gives one refund entry and status refunded
        level: unit"""
        oid = self.paid_order(amount=800, key="k1")
        cid = self.app.order(oid)["charge_id"]
        ev = self.event("evt_r", "charge.refunded", oid, cid)
        self.app.handle_webhook(ev)
        self.app.handle_webhook(ev)
        self.app.handle_webhook(self.event("evt_r2", "charge.refunded", oid, cid))
        self.assertEqual(self.app.order(oid)["status"], "refunded")
        self.assertEqual([e["kind"] for e in self.app.ledger()], ["charge", "refund"])
        self.app.cancel(oid)
        self.assertEqual(self.gw.refunds, [])

    def test_unknown_events_are_ignored(self):
        """features: M02
        acceptance: AC03
        expect: unknown types and unknown orders change nothing; a refund event never pays
        level: unit"""
        oid = self.app.create_order("alice", 500)
        self.app.handle_webhook(self.event("e1", "charge.disputed", oid, "ch_1"))
        self.app.handle_webhook(self.event("e2", "charge.succeeded", "ord_missing", "ch_1"))
        self.app.handle_webhook(self.event("e3", "charge.refunded", oid, "ch_1"))
        self.assertEqual(self.app.order(oid)["status"], "pending")
        self.assertEqual(self.app.ledger(), [])
        with self.assertRaises(InvalidRequest):
            self.app.handle_webhook({"type": "charge.succeeded", "order_id": oid})

    def test_failed_write_on_webhook_leaves_order_unchanged(self):
        """features: M02
        acceptance: AC04
        expect: StoreError, order unchanged and event not recorded; redelivery applies it once
        level: database"""
        oid = self.app.create_order("alice", 500)
        ev = self.event("evt_1", "charge.succeeded", oid, "ch_5")
        self.store.fail_next_write = True
        with self.assertRaises(StoreError):
            self.app.handle_webhook(ev)
        self.assertEqual(self.app.order(oid)["status"], "pending")
        self.app.handle_webhook(ev)
        self.app.handle_webhook(ev)
        self.assertEqual(self.app.order(oid)["status"], "paid")
        self.assertEqual(len(self.app.ledger()), 1)

    def test_late_charge_on_cancelled_order_is_refunded_once(self):
        """features: M02, M05
        acceptance: AC03, AC05
        expect: money arriving for a cancelled order is refunded once
        level: interaction"""
        oid = self.app.create_order("alice", 300)
        self.app.cancel(oid)
        ev = self.event("evt_l", "charge.succeeded", oid, "ch_7")
        self.app.handle_webhook(ev)
        self.app.handle_webhook(ev)
        self.assertEqual(self.app.order(oid)["status"], "refunded")
        self.assertEqual(self.gw.refunds, ["ch_7"])
        self.assertEqual([e["kind"] for e in self.app.ledger()], ["charge", "refund"])


class V3Cancel(Base):
    def test_cancel_pending_order(self):
        """features: M05, M04
        acceptance: AC05
        expect: a pending order is cancelled with no refund; cancelling again changes nothing
        level: unit"""
        oid = self.app.create_order("alice", 100)
        self.app.cancel(oid)
        self.app.cancel(oid)
        self.assertEqual(self.app.order(oid)["status"], "cancelled")
        self.assertEqual(self.gw.refunds, [])
        self.assertEqual(self.app.ledger(), [])

    def test_cancel_paid_order_refunds_exactly_once(self):
        """features: M05
        acceptance: AC05
        expect: one gateway refund, status refunded, one ledger refund, even when cancelled twice
        level: unit"""
        oid = self.paid_order(amount=1500, key="k1")
        cid = self.app.order(oid)["charge_id"]
        self.app.cancel(oid)
        self.app.cancel(oid)
        self.assertEqual(self.gw.refunds, [cid])
        self.assertEqual(self.app.order(oid)["status"], "refunded")
        self.assertEqual([e["kind"] for e in self.app.ledger()], ["charge", "refund"])
        self.app.handle_webhook({"id": "evt_r", "type": "charge.refunded", "order_id": oid, "charge_id": cid})
        self.assertEqual(len(self.app.ledger()), 2)

    def test_failed_write_on_cancel_leaves_order_unchanged(self):
        """features: M05
        acceptance: AC04
        expect: StoreError, order still paid, no refund sent; the retry refunds once
        level: database"""
        oid = self.paid_order(amount=1500, key="k1")
        self.store.fail_next_write = True
        with self.assertRaises(StoreError):
            self.app.cancel(oid)
        self.assertEqual(self.app.order(oid)["status"], "paid")
        self.assertEqual(self.gw.refunds, [])
        self.app.cancel(oid)
        self.assertEqual(len(self.gw.refunds), 1)
        self.assertEqual(self.app.order(oid)["status"], "refunded")

    def test_journey_pay_webhook_cancel_ledger(self):
        """features: M07, M04, M01, M02, M05, M06
        acceptance: AC10
        expect: create, pay with a retry after a timeout, duplicate webhook, cancel twice: one charge and one refund everywhere
        level: journey"""
        oid = self.app.create_order("carol", 4200)
        self.gw.timeout_after_success = True
        try:
            self.app.pay(oid, "checkout-1")
        except gateway.GatewayTimeout:
            pass
        self.app.pay(oid, "checkout-1")
        cid = self.app.order(oid)["charge_id"]
        ev = {"id": "evt_100", "type": "charge.succeeded", "order_id": oid, "charge_id": cid}
        self.app.handle_webhook(ev)
        self.app.handle_webhook(ev)
        self.app.cancel(oid)
        self.app.cancel(oid)
        self.assertEqual(self.app.order(oid), {"status": "refunded", "amount_cents": 4200, "charge_id": cid})
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(self.gw.refunds, [cid])
        self.assertEqual(self.app.ledger(), [{"order_id": oid, "kind": "charge", "amount_cents": 4200},
                                             {"order_id": oid, "kind": "refund", "amount_cents": 4200}])


class V4Renewals(Base):
    def test_renewing_same_period_creates_one_order(self):
        """features: M03, M07
        acceptance: AC07
        expect: one order per subscription per period; a new period creates a new order
        level: unit"""
        sub = {"id": "sub_1", "customer": "dave", "price_cents": 999}
        first = self.app.renew(sub, "2026-11")
        again = self.app.renew(sub, "2026-11")
        nxt = self.app.renew(sub, "2026-12")
        self.assertEqual(first, again)
        self.assertNotEqual(first, nxt)
        self.assertEqual(self.app.order(first), {"status": "pending", "amount_cents": 999, "charge_id": None})
        with self.assertRaises(InvalidRequest):
            self.app.renew({"id": "sub_2", "customer": "erin", "price_cents": 9.99}, "2026-11")

    def test_journey_renewal_then_payment(self):
        """features: M03, M07, M01, M06
        acceptance: AC07
        expect: a renewal's order is paid once even if the renewal and the payment are retried
        level: journey"""
        sub = {"id": "sub_1", "customer": "dave", "price_cents": 999}
        oid = self.app.renew(sub, "2026-11")
        self.app.pay(oid, "renew-sub_1-2026-11")
        self.assertEqual(self.app.renew(sub, "2026-11"), oid)
        self.app.pay(self.app.renew(sub, "2026-11"), "renew-sub_1-2026-11")
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(self.app.ledger(), [{"order_id": oid, "kind": "charge", "amount_cents": 999}])


if __name__ == "__main__":
    unittest.main()
