# Naive: A's charge code with the client's key, A's webhook handler, C's cancel. Each worked alone.
class StoreError(Exception):
    pass


class App:
    def __init__(self, gateway, store=None):
        self.gw, self.store, self.orders, self.entries = gateway, store, {}, []

    def create_order(self, customer, amount_cents):
        i = len(self.orders) + 1
        self.orders[i] = {"status": "pending", "amount_cents": amount_cents, "charge_id": None}
        return i

    def pay(self, order_id, key):
        o = self.orders[order_id]
        o["charge_id"] = self.gw.charge(o["amount_cents"], key)
        self.entries.append({"order_id": order_id, "kind": "charge", "amount_cents": o["amount_cents"]})
        if self.store is not None and self.store.fail_next_write:
            self.store.fail_next_write = False
            raise StoreError("write failed")
        o["status"] = "paid"

    def handle_webhook(self, event):
        o = self.orders.get(event.get("order_id"))
        if o and event["type"] == "charge.succeeded":
            o["status"] = "paid"
            self.entries.append({"order_id": event["order_id"], "kind": "charge", "amount_cents": o["amount_cents"]})
        elif o and event["type"] == "charge.refunded":
            self.entries.append({"order_id": event["order_id"], "kind": "refund", "amount_cents": o["amount_cents"]})

    def cancel(self, order_id):
        o = self.orders[order_id]
        if o["status"] == "paid":
            self.gw.refund(o["charge_id"])
            self.entries.append({"order_id": order_id, "kind": "refund", "amount_cents": o["amount_cents"]})
            o["status"] = "refunded"
        else:
            o["status"] = "cancelled"

    def order(self, order_id):
        return dict(self.orders[order_id])

    def ledger(self):
        return list(self.entries)


def create_app(gateway, store=None):
    return App(gateway, store)
