import copy


class StoreError(Exception):
    pass


class App:
    def __init__(self, gateway, store=None):
        self.gw, self.store = gateway, store
        self.orders, self.entries, self.seen_events = {}, [], set()

    def _commit(self, order_id, new_order, entries=()):
        """Apply an order change and its ledger entries together, or not at all."""
        if self.store is not None and getattr(self.store, "fail_next_write", False):
            self.store.fail_next_write = False
            raise StoreError("write failed")
        self.orders[order_id] = new_order
        self.entries.extend(entries)

    def create_order(self, customer, amount_cents):
        i = len(self.orders) + 1
        self.orders[i] = {"status": "pending", "amount_cents": amount_cents, "charge_id": None,
                          "customer": customer}
        return i

    def pay(self, order_id, key):
        o = self.orders[order_id]
        if o["status"] == "paid":
            return o["charge_id"]
        if o["status"] != "pending":
            raise ValueError(f"cannot pay a {o['status']} order")
        cid = self.gw.charge(o["amount_cents"], f"order-{order_id}")  # one key per order: never two charges
        new = dict(o, status="paid", charge_id=cid)
        self._commit(order_id, new, [{"order_id": order_id, "kind": "charge", "amount_cents": o["amount_cents"]}])
        return cid

    def handle_webhook(self, event):
        if event["id"] in self.seen_events:
            return
        o = self.orders.get(event.get("order_id"))
        if o is None:
            self.seen_events.add(event["id"])
            return
        if event["type"] == "charge.succeeded" and o["status"] == "pending":
            self._commit(event["order_id"], dict(o, status="paid", charge_id=event["charge_id"]),
                         [{"order_id": event["order_id"], "kind": "charge", "amount_cents": o["amount_cents"]}])
        elif event["type"] == "charge.refunded" and o["status"] == "paid":
            self._commit(event["order_id"], dict(o, status="refunded"),
                         [{"order_id": event["order_id"], "kind": "refund", "amount_cents": o["amount_cents"]}])
        self.seen_events.add(event["id"])

    def cancel(self, order_id):
        o = self.orders[order_id]
        if o["status"] == "pending":
            self._commit(order_id, dict(o, status="cancelled"))
        elif o["status"] == "paid":
            self.gw.refund(o["charge_id"])
            self._commit(order_id, dict(o, status="refunded"),
                         [{"order_id": order_id, "kind": "refund", "amount_cents": o["amount_cents"]}])

    def order(self, order_id):
        return copy.deepcopy(self.orders[order_id])

    def ledger(self):
        return list(self.entries)


def create_app(gateway, store=None):
    return App(gateway, store)
