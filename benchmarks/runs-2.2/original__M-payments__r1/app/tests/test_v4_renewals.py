import unittest

from tests.helpers import make


class RenewalTest(unittest.TestCase):
    def test_renew_creates_order(self):
        """features: M05, M01
        acceptance: AC11
        expect: a renewal creates a pending order for the customer at the subscription price
        level: unit"""
        _, app = make()
        oid = app.renew({"id": "sub_1", "customer": "cus", "price": 999})
        self.assertEqual(app.order(oid), {"status": "pending", "amount_cents": 999, "charge_id": None})

    def test_same_period_renewed_once(self):
        """features: M05
        acceptance: AC11
        expect: renewing the same period twice returns the same order; a new period makes a new order
        level: unit"""
        _, app = make()
        sub = {"id": "sub_1", "customer": "cus", "price": 999}
        a, b = app.renew(sub, "2026-11"), app.renew(sub, "2026-11")
        c = app.renew(sub, "2026-12")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        with self.assertRaises(ValueError):
            app.renew({"customer": "cus", "price": 999}, "2026-11")

    def test_renewal_journey_pay_and_cancel(self):
        """features: M05, M02, M04, M03
        acceptance: AC11
        expect: renewal order is paid once with retries, confirmed by webhook, and refunded once on cancel
        level: journey"""
        gw, app = make()
        oid = app.renew({"id": "sub_9", "customer": "cus", "price": 1500}, "2026-11")
        cid = app.pay(oid, "renew-sub_9-2026-11")
        app.pay(oid, "renew-sub_9-2026-11")
        app.handle_webhook({"id": "evt_1", "type": "charge.succeeded", "order_id": oid, "charge_id": cid})
        app.cancel(oid)
        self.assertEqual(len(gw.charges), 1)
        self.assertEqual(len(gw.refunds), 1)
        self.assertEqual(app.ledger(), [{"order_id": oid, "kind": "charge", "amount_cents": 1500},
                                        {"order_id": oid, "kind": "refund", "amount_cents": 1500}])


if __name__ == "__main__":
    unittest.main()
