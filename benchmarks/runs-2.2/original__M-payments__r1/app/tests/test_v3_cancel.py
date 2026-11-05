import unittest

from tests.helpers import billing, make


class CancelTest(unittest.TestCase):
    def test_cancel_pending_no_refund(self):
        """features: M04, M01
        acceptance: AC09
        expect: a pending order becomes cancelled, no gateway refund, no ledger entry, cannot be paid after
        level: unit"""
        gw, app = make()
        oid = app.create_order("cus", 100)
        self.assertEqual(app.cancel(oid), "cancelled")
        self.assertEqual(app.order(oid)["status"], "cancelled")
        self.assertEqual(gw.refunds, [])
        self.assertEqual(app.ledger(), [])
        with self.assertRaises(billing.InvalidState):
            app.pay(oid, "k")
        self.assertEqual(gw.charges, {})

    def test_cancel_paid_refunds_exactly_once(self):
        """features: M04, M02
        acceptance: AC08
        expect: cancelling a paid order twice refunds once, status refunded, ledger charge then refund
        level: interaction"""
        gw, app = make()
        oid = app.create_order("cus", 1200)
        cid = app.pay(oid, "k")
        self.assertEqual(app.cancel(oid), "refunded")
        self.assertEqual(app.cancel(oid), "refunded")
        self.assertEqual(gw.refunds, [cid])
        self.assertEqual(app.order(oid), {"status": "refunded", "amount_cents": 1200, "charge_id": cid})
        self.assertEqual(app.ledger(), [{"order_id": oid, "kind": "charge", "amount_cents": 1200},
                                        {"order_id": oid, "kind": "refund", "amount_cents": 1200}])

    def test_cancel_then_refund_webhook_not_applied_twice(self):
        """features: M04, M03
        acceptance: AC08
        expect: the gateway's charge.refunded webhook after a cancel adds no second refund
        level: interaction"""
        gw, app = make()
        oid = app.create_order("cus", 500)
        cid = app.pay(oid, "k")
        app.cancel(oid)
        self.assertFalse(app.handle_webhook({"id": "evt_r", "type": "charge.refunded", "order_id": oid, "charge_id": cid}))
        self.assertEqual(len(gw.refunds), 1)
        self.assertEqual([x["kind"] for x in app.ledger()], ["charge", "refund"])

    def test_write_failure_before_refund(self):
        """features: M04
        acceptance: AC10
        expect: StoreError on cancel leaves the paid order unchanged; the retry refunds exactly once
        level: database"""
        store = billing.Store()
        gw, app = make(store)
        oid = app.create_order("cus", 500)
        cid = app.pay(oid, "k")
        before = app.order(oid)
        store.fail_next_write = True
        with self.assertRaises(billing.StoreError):
            app.cancel(oid)
        self.assertEqual(app.order(oid), before)
        self.assertEqual(len(app.ledger()), 1)
        app.cancel(oid)
        app.cancel(oid)
        self.assertEqual(gw.refunds, [cid])
        self.assertEqual(app.order(oid)["status"], "refunded")
        self.assertEqual(len(app.ledger()), 2)

    def test_write_failure_after_refund_never_refunds_again(self):
        """features: M04
        acceptance: AC10
        expect: if the write after the gateway refund fails, the order stays paid and a retry completes without a second refund
        level: database"""
        store = billing.Store()
        gw, app = make(store)
        oid = app.create_order("cus", 500)
        app.pay(oid, "k")
        original_refund = gw.refund

        def refund_then_fail(charge_id):
            rid = original_refund(charge_id)
            store.fail_next_write = True
            return rid
        gw.refund = refund_then_fail
        with self.assertRaises(billing.StoreError):
            app.cancel(oid)
        self.assertEqual(app.order(oid)["status"], "paid")
        gw.refund = original_refund
        self.assertEqual(app.cancel(oid), "refunded")
        self.assertEqual(len(gw.refunds), 1)
        self.assertEqual([x["kind"] for x in app.ledger()], ["charge", "refund"])

    def test_late_charge_on_cancelled_order_is_refunded_once(self):
        """features: M04, M03, M02
        acceptance: AC08
        expect: pay times out, the order is cancelled, then charge.succeeded arrives: the charge is refunded once
        level: interaction"""
        gw, app = make()
        oid = app.create_order("cus", 700)
        gw.timeout_after_success = True
        with self.assertRaises(billing.GatewayTimeout):
            app.pay(oid, "k")
        app.cancel(oid)
        cid = next(iter(gw.charges))
        e = {"id": "evt_late", "type": "charge.succeeded", "order_id": oid, "charge_id": cid}
        self.assertTrue(app.handle_webhook(e))
        self.assertFalse(app.handle_webhook(e))
        app.cancel(oid)
        self.assertEqual(gw.refunds, [cid])
        self.assertEqual(app.order(oid)["status"], "refunded")
        self.assertEqual([x["kind"] for x in app.ledger()], ["charge", "refund"])


if __name__ == "__main__":
    unittest.main()
