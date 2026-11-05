import unittest

from tests.helpers import billing, gateway, make


class OrdersTest(unittest.TestCase):
    def test_create_order_is_pending(self):
        """features: M01
        acceptance: AC01
        expect: a new order is pending with its amount and no charge
        level: unit"""
        _, app = make()
        oid = app.create_order("cus_1", 500)
        self.assertEqual(app.order(oid), {"status": "pending", "amount_cents": 500, "charge_id": None})
        self.assertEqual(app.ledger(), [])

    def test_invalid_amounts_and_missing_order(self):
        """features: M01
        acceptance: AC01
        expect: non-positive, non-integer and bool amounts are refused; unknown ids raise OrderNotFound
        level: unit"""
        _, app = make()
        for bad in (0, -5, 1.5, "500", True, None):
            with self.assertRaises(ValueError):
                app.create_order("cus", bad)
        with self.assertRaises(billing.OrderNotFound):
            app.order("nope")
        with self.assertRaises(KeyError):
            app.pay("nope", "k")

    def test_create_order_write_failure_creates_nothing(self):
        """features: M01
        acceptance: AC01
        expect: a failed write raises StoreError and no order exists afterwards
        level: database"""
        store = billing.Store()
        _, app = make(store)
        store.fail_next_write = True
        with self.assertRaises(billing.StoreError):
            app.create_order("cus", 100)
        self.assertFalse(store.fail_next_write)
        oid = app.create_order("cus", 100)
        self.assertEqual(oid, "ord_1")


class PaymentsTest(unittest.TestCase):
    def test_pay_marks_paid_and_ledgers_once(self):
        """features: M02, M01
        acceptance: AC02
        expect: paying charges the gateway once, order paid with the charge id, one ledger charge
        level: unit"""
        gw, app = make()
        oid = app.create_order("cus", 700)
        cid = app.pay(oid, "key-1")
        self.assertEqual(app.order(oid), {"status": "paid", "amount_cents": 700, "charge_id": cid})
        self.assertEqual(gw.charges, {cid: 700})
        self.assertEqual(app.ledger(), [{"order_id": oid, "kind": "charge", "amount_cents": 700}])

    def test_retry_same_key_never_charges_twice(self):
        """features: M02
        acceptance: AC02
        expect: three pays with the same key give one gateway charge and one ledger entry
        level: unit"""
        gw, app = make()
        oid = app.create_order("cus", 300)
        ids = {app.pay(oid, "k"), app.pay(oid, "k"), app.pay(oid, "k")}
        self.assertEqual(len(ids), 1)
        self.assertEqual(len(gw.charges), 1)
        self.assertEqual(len(app.ledger()), 1)

    def test_paid_order_with_new_key_not_charged(self):
        """features: M02
        acceptance: AC02
        expect: paying an already paid order with a different key does not charge again
        level: unit"""
        gw, app = make()
        oid = app.create_order("cus", 300)
        cid = app.pay(oid, "k1")
        self.assertEqual(app.pay(oid, "k2"), cid)
        self.assertEqual(len(gw.charges), 1)
        self.assertEqual(len(app.ledger()), 1)

    def test_key_reused_for_other_order_refused(self):
        """features: M02
        acceptance: AC02
        expect: a key already used for order 1 is refused for order 2, which stays pending and uncharged
        level: unit"""
        gw, app = make()
        o1, o2 = app.create_order("a", 100), app.create_order("b", 200)
        app.pay(o1, "shared")
        with self.assertRaises(billing.IdempotencyKeyReused):
            app.pay(o2, "shared")
        self.assertEqual(app.order(o2)["status"], "pending")
        self.assertEqual(len(gw.charges), 1)

    def test_missing_key_refused(self):
        """features: M02
        acceptance: AC02
        expect: pay without an idempotency key is refused before any charge
        level: unit"""
        gw, app = make()
        oid = app.create_order("cus", 100)
        for bad in (None, ""):
            with self.assertRaises(ValueError):
                app.pay(oid, bad)
        self.assertEqual(gw.charges, {})

    def test_timeout_then_retry_same_key_charges_once(self):
        """features: M02, M01
        acceptance: AC03
        expect: a timeout after a successful charge leaves the order pending; the retry gets the same charge
        level: interaction"""
        gw, app = make()
        oid = app.create_order("cus", 900)
        gw.timeout_after_success = True
        with self.assertRaises(gateway.GatewayTimeout):
            app.pay(oid, "k")
        self.assertEqual(app.order(oid), {"status": "pending", "amount_cents": 900, "charge_id": None})
        self.assertEqual(app.ledger(), [])
        cid = app.pay(oid, "k")
        self.assertEqual(app.order(oid)["status"], "paid")
        self.assertEqual(gw.charges, {cid: 900})
        self.assertEqual(len(app.ledger()), 1)

    def test_timeout_then_retry_other_key_charges_once(self):
        """features: M02
        acceptance: AC03
        expect: after a timeout, a retry with a new key reuses the first gateway key, so no second charge
        level: interaction"""
        gw, app = make()
        oid = app.create_order("cus", 900)
        gw.timeout_after_success = True
        with self.assertRaises(gateway.GatewayTimeout):
            app.pay(oid, "k1")
        app.pay(oid, "k2")
        self.assertEqual(len(gw.charges), 1)
        self.assertEqual(app.order(oid)["status"], "paid")
        self.assertEqual(len(app.ledger()), 1)

    def test_timeout_exception_importable_from_module(self):
        """features: M02
        acceptance: AC03
        expect: billing re-exports the gateway's GatewayTimeout
        level: unit"""
        self.assertIs(billing.GatewayTimeout, gateway.GatewayTimeout)

    def test_write_failure_during_pay_leaves_order_unchanged(self):
        """features: M02, M01
        acceptance: AC04
        expect: StoreError, order unchanged and no ledger entry; the retry charges exactly once
        level: database"""
        store = billing.Store()
        gw, app = make(store)
        oid = app.create_order("cus", 400)
        before = app.order(oid)
        store.fail_next_write = True
        with self.assertRaises(billing.StoreError):
            app.pay(oid, "k")
        self.assertEqual(app.order(oid), before)
        self.assertEqual(app.ledger(), [])
        app.pay(oid, "k")
        self.assertEqual(len(gw.charges), 1)
        self.assertEqual(app.order(oid)["status"], "paid")
        self.assertEqual(len(app.ledger()), 1)

    def test_write_failure_after_charge_retry_collects_same_charge(self):
        """features: M02
        acceptance: AC04
        expect: if the write after a successful charge fails, the order stays pending and a retry with any key does not charge again
        level: database"""
        store = billing.Store()
        gw, app = make(store)
        oid = app.create_order("cus", 400)
        original_charge = gw.charge

        def charge_then_fail(amount, key):
            cid = original_charge(amount, key)
            store.fail_next_write = True
            return cid
        gw.charge = charge_then_fail
        with self.assertRaises(billing.StoreError):
            app.pay(oid, "k1")
        self.assertEqual(app.order(oid), {"status": "pending", "amount_cents": 400, "charge_id": None})
        gw.charge = original_charge
        app.pay(oid, "k2")
        self.assertEqual(len(gw.charges), 1)
        self.assertEqual(app.order(oid)["status"], "paid")
        self.assertEqual(len(app.ledger()), 1)

    def test_foreign_store_object_controls_failures(self):
        """features: M02, M01
        acceptance: AC04
        expect: any object with fail_next_write works as the store; its flag makes the next write fail once
        level: database"""
        class FlagStore:
            fail_next_write = False
        flag = FlagStore()
        gw, app = make(flag)
        oid = app.create_order("cus", 100)
        flag.fail_next_write = True
        with self.assertRaises(billing.StoreError):
            app.pay(oid, "k")
        self.assertFalse(flag.fail_next_write)
        self.assertEqual(app.order(oid)["status"], "pending")
        app.pay(oid, "k")
        self.assertEqual(app.order(oid)["status"], "paid")

    def test_default_store_exposed(self):
        """features: M01
        acceptance: AC04
        expect: create_app without a store exposes app.store with fail_next_write False
        level: unit"""
        _, app = make()
        self.assertIs(app.store.fail_next_write, False)
        app.store.fail_next_write = True
        with self.assertRaises(billing.StoreError):
            app.create_order("c", 1)


if __name__ == "__main__":
    unittest.main()
