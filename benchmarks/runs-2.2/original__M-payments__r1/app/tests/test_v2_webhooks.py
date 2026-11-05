import unittest

from tests.helpers import billing, make


def ev(eid, etype, oid, cid):
    return {"id": eid, "type": etype, "order_id": oid, "charge_id": cid}


class WebhookTest(unittest.TestCase):
    def test_succeeded_webhook_marks_pending_order_paid(self):
        """features: M03, M01
        acceptance: AC05
        expect: charge.succeeded moves a pending order to paid with the event's charge id and one ledger charge
        level: unit"""
        _, app = make()
        oid = app.create_order("cus", 250)
        self.assertTrue(app.handle_webhook(ev("evt_1", "charge.succeeded", oid, "ch_9")))
        self.assertEqual(app.order(oid), {"status": "paid", "amount_cents": 250, "charge_id": "ch_9"})
        self.assertEqual(app.ledger(), [{"order_id": oid, "kind": "charge", "amount_cents": 250}])

    def test_duplicate_delivery_applied_once(self):
        """features: M03
        acceptance: AC05
        expect: the same event delivered three times is applied once
        level: unit"""
        _, app = make()
        oid = app.create_order("cus", 250)
        e = ev("evt_1", "charge.succeeded", oid, "ch_1")
        results = [app.handle_webhook(dict(e)) for _ in range(3)]
        self.assertEqual(results, [True, False, False])
        self.assertEqual(len(app.ledger()), 1)

    def test_webhook_after_pay_adds_nothing(self):
        """features: M03, M02
        acceptance: AC06
        expect: pay then charge.succeeded for the same charge leaves one ledger charge; pay again does not charge
        level: interaction"""
        gw, app = make()
        oid = app.create_order("cus", 800)
        cid = app.pay(oid, "k")
        self.assertFalse(app.handle_webhook(ev("evt_1", "charge.succeeded", oid, cid)))
        app.pay(oid, "k")
        self.assertEqual(len(app.ledger()), 1)
        self.assertEqual(len(gw.charges), 1)

    def test_webhook_after_timeout_then_retry(self):
        """features: M03, M02
        acceptance: AC06
        expect: timeout, then the webhook confirms the charge, then the client retry neither charges nor ledgers again
        level: interaction"""
        gw, app = make()
        oid = app.create_order("cus", 800)
        gw.timeout_after_success = True
        with self.assertRaises(billing.GatewayTimeout):
            app.pay(oid, "k")
        cid = next(iter(gw.charges))
        self.assertTrue(app.handle_webhook(ev("evt_1", "charge.succeeded", oid, cid)))
        self.assertEqual(app.pay(oid, "k"), cid)
        self.assertEqual(len(gw.charges), 1)
        self.assertEqual(len(app.ledger()), 1)

    def test_refunded_webhook_refunds_paid_order_once(self):
        """features: M03, M01
        acceptance: AC05
        expect: charge.refunded moves a paid order to refunded with one ledger refund; redelivery does nothing
        level: unit"""
        gw, app = make()
        oid = app.create_order("cus", 600)
        cid = app.pay(oid, "k")
        e = ev("evt_r", "charge.refunded", oid, cid)
        self.assertTrue(app.handle_webhook(e))
        self.assertFalse(app.handle_webhook(e))
        self.assertEqual(app.order(oid)["status"], "refunded")
        kinds = [x["kind"] for x in app.ledger()]
        self.assertEqual(kinds, ["charge", "refund"])
        self.assertEqual(gw.refunds, [])  # the gateway already refunded; the app does not refund again

    def test_ignored_events(self):
        """features: M03
        acceptance: AC05
        expect: unknown orders, unknown types, wrong charge ids and refunds of pending orders change nothing
        level: unit"""
        _, app = make()
        oid = app.create_order("cus", 100)
        self.assertFalse(app.handle_webhook(ev("e1", "charge.succeeded", "missing", "ch_1")))
        self.assertFalse(app.handle_webhook(ev("e2", "charge.disputed", oid, "ch_1")))
        self.assertFalse(app.handle_webhook(ev("e3", "charge.refunded", oid, "ch_1")))
        app.pay(oid, "k")
        self.assertFalse(app.handle_webhook(ev("e4", "charge.refunded", oid, "ch_other")))
        self.assertEqual(app.order(oid)["status"], "paid")
        self.assertEqual(len(app.ledger()), 1)
        with self.assertRaises(ValueError):
            app.handle_webhook({"type": "charge.succeeded", "order_id": oid})

    def test_write_failure_leaves_order_unchanged_and_redelivery_applies(self):
        """features: M03
        acceptance: AC07
        expect: StoreError while applying an event leaves the order pending; the redelivered event applies once
        level: database"""
        store = billing.Store()
        _, app = make(store)
        oid = app.create_order("cus", 100)
        e = ev("evt_1", "charge.succeeded", oid, "ch_1")
        store.fail_next_write = True
        with self.assertRaises(billing.StoreError):
            app.handle_webhook(e)
        self.assertEqual(app.order(oid)["status"], "pending")
        self.assertEqual(app.ledger(), [])
        self.assertTrue(app.handle_webhook(e))
        self.assertFalse(app.handle_webhook(e))
        self.assertEqual(len(app.ledger()), 1)


if __name__ == "__main__":
    unittest.main()
