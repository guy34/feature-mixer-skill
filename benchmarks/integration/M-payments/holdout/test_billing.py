import unittest
import billing as m
import gateway as g


class Store:
    fail_next_write = False


class BillingHoldout(unittest.TestCase):
    def setUp(self):
        self.gw, self.store = g.FakeGateway(), Store()
        self.app = m.create_app(self.gw, self.store)
        self.o = self.app.create_order("ana", 1250)

    def charges(self):
        return [e for e in self.app.ledger() if e["kind"] == "charge"]

    def test_pay(self):
        self.app.pay(self.o, "k1")
        self.assertEqual(self.app.order(self.o)["status"], "paid")
        self.assertEqual(len(self.gw.charges), 1)

    def test_same_key_twice_charges_once(self):
        self.app.pay(self.o, "k1")
        self.app.pay(self.o, "k1")
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(len(self.charges()), 1)

    def test_paid_order_is_not_charged_again_with_a_new_key(self):
        self.app.pay(self.o, "k1")
        self.app.pay(self.o, "k2")
        self.assertEqual(len(self.gw.charges), 1)

    def test_duplicate_webhook_applies_once(self):
        self.app.pay(self.o, "k1")
        cid = self.app.order(self.o)["charge_id"]
        ev = {"id": "evt_1", "type": "charge.succeeded", "order_id": self.o, "charge_id": cid}
        for _ in range(3):
            self.app.handle_webhook(ev)
        self.assertEqual(len(self.charges()), 1)
        self.assertEqual(self.app.order(self.o)["status"], "paid")

    def test_retry_after_timeout_charges_once(self):
        self.gw.timeout_after_success = True
        # The task requires one charge and a consistent order, not a particular way of handling the timeout:
        # the app may surface it to the client or retry with the same key itself.
        try:
            self.app.pay(self.o, "k1")
        except Exception:
            pass
        self.assertIn(self.app.order(self.o)["status"], ("pending", "paid"))
        self.app.pay(self.o, "k1")
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(self.app.order(self.o)["status"], "paid")
        self.assertEqual(len(self.charges()), 1)

    def test_failed_write_leaves_order_unchanged(self):
        self.store.fail_next_write = True
        with self.assertRaises(m.StoreError):
            self.app.pay(self.o, "k1")
        self.assertEqual(self.app.order(self.o)["status"], "pending")
        self.assertEqual(self.charges(), [])
        self.app.pay(self.o, "k1")
        self.assertEqual(self.app.order(self.o)["status"], "paid")
        self.assertEqual(len(self.gw.charges), 1)

    def test_cancel_after_payment_refunds_once(self):
        self.app.pay(self.o, "k1")
        self.app.cancel(self.o)
        self.app.cancel(self.o)
        self.assertEqual(self.app.order(self.o)["status"], "refunded")
        self.assertEqual(len(self.gw.refunds), 1)
        self.app.handle_webhook({"id": "evt_r", "type": "charge.refunded", "order_id": self.o,
                                 "charge_id": self.app.order(self.o)["charge_id"]})
        self.assertEqual([e["kind"] for e in self.app.ledger()].count("refund"), 1)

    def test_cancel_unpaid_order_charges_nothing(self):
        self.app.cancel(self.o)
        self.assertEqual(self.app.order(self.o)["status"], "cancelled")
        self.assertEqual((self.gw.charges, self.gw.refunds), ({}, []))
        with self.assertRaises(Exception):
            self.app.pay(self.o, "k9")
        self.assertEqual(self.gw.charges, {})

    def test_unknown_order_webhook_is_harmless(self):
        self.app.handle_webhook({"id": "evt_x", "type": "charge.succeeded", "order_id": 999, "charge_id": "ch_9"})
        self.assertEqual(self.app.ledger(), [])
