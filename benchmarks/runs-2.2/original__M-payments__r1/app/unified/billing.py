"""Unified billing: orders, idempotent payments, exactly-once webhooks, cancel with refund, renewals.

Built by Feature Mixer from three source apps:
  Billfold (A)  charging through a gateway and its webhooks   -> pay(), handle_webhook()
  Subscribe (B) subscriptions that create orders              -> renew()
  Orderly (C)   order states pending/paid/cancelled/refunded  -> create_order(), cancel(), order()

Guarantees (see mixer/design/architecture.md, decisions D01-D13):
  * never charge twice: the client's idempotency key is required; the first key used for an order is
    recorded *before* the gateway is called and reused for every later attempt on that order, and an
    order that is already paid is never charged again;
  * never apply a webhook twice: processed event ids are stored in the same atomic write as the change;
  * consistent state on gateway timeouts and failed writes: every state change is one all-or-nothing
    store write; a timeout leaves the order pending with its attempt recorded so a retry collects the
    original charge instead of making a new one;
  * a cancelled paid order is refunded exactly once: a refund record is written before the gateway's
    (non-idempotent) refund call, and once it exists the gateway is never asked to refund that order again.

Usage:
    app = create_app(gateway, store=None)
    order_id = app.create_order(customer, amount_cents)
    app.pay(order_id, key)
    app.handle_webhook({"id", "type", "order_id", "charge_id"})
    app.cancel(order_id)
    app.order(order_id) -> {"status", "amount_cents", "charge_id"}
    app.ledger() -> [{"order_id", "kind", "amount_cents"}]
    app.renew(subscription, period=None)
"""

import copy
import threading

try:  # re-export the gateway's timeout so callers can import it from here
    from gateway import GatewayTimeout  # noqa: F401
except Exception:  # pragma: no cover - gateway.py not on the path
    class GatewayTimeout(Exception):
        """The gateway did not answer; the operation may or may not have happened."""


__all__ = [
    "create_app", "BillingApp", "Store", "StoreError", "BillingError", "OrderNotFound",
    "InvalidState", "IdempotencyKeyReused", "RefundOutcomeUnknown", "GatewayTimeout",
    "PENDING", "PAID", "CANCELLED", "REFUNDED", "STATES",
]

# --------------------------------------------------------------------------- errors

PENDING, PAID, CANCELLED, REFUNDED = "pending", "paid", "cancelled", "refunded"
STATES = (PENDING, PAID, CANCELLED, REFUNDED)

# Allowed status changes (D01, D02, D13). Anything else is refused.
TRANSITIONS = {
    PENDING: {PAID, CANCELLED},
    PAID: {REFUNDED},
    CANCELLED: {REFUNDED},  # only when a charge arrives late for a cancelled order and is refunded (D13)
    REFUNDED: set(),
}


class StoreError(Exception):
    """A store write failed; nothing from that write was applied."""


class BillingError(Exception):
    """Base class for billing rule violations."""


class OrderNotFound(BillingError, KeyError):
    """No order has this id."""


class InvalidState(BillingError, ValueError):
    """The operation is not allowed in the order's current status."""


class IdempotencyKeyReused(BillingError, ValueError):
    """The idempotency key was already used for a different order."""


class RefundOutcomeUnknown(BillingError, RuntimeError):
    """The gateway failed during a refund in a way that leaves its outcome unknown."""


# --------------------------------------------------------------------------- store

class Store:
    """In-memory store whose writes are all-or-nothing.

    Set ``fail_next_write = True`` to make the next write raise StoreError and change nothing.
    """

    TABLES = ("orders", "ledger", "keys", "order_keys", "refunds", "events", "renewals", "meta")

    def __init__(self, flag_source=None):
        self.fail_next_write = False
        self._flag_source = flag_source
        self._data = {"orders": {}, "ledger": [], "keys": {}, "order_keys": {}, "refunds": {},
                      "events": {}, "renewals": {}, "meta": {"seq": 0}}
        self.writes = 0

    # reads return copies so callers can never change stored state by accident
    def get(self, table, key, default=None):
        value = self._data[table].get(key, default)
        return copy.deepcopy(value)

    def has(self, table, key):
        return key in self._data[table]

    def all(self, table):
        return copy.deepcopy(self._data[table])

    def write(self, ops):
        """Apply a list of operations atomically.

        ops: ("set", table, key, value) | ("delete", table, key) | ("append", table, value)
        Every operation is checked before anything changes, and the failure switch is checked first,
        so a write either applies completely or not at all.
        """
        source = self._flag_source if self._flag_source is not None else self
        if getattr(source, "fail_next_write", False):
            source.fail_next_write = False
            raise StoreError("store write failed; nothing was changed")
        prepared = []
        for op in ops:
            kind, table = op[0], op[1]
            if table not in self.TABLES:
                raise ValueError(f"unknown table {table!r}")
            if kind == "set":
                prepared.append((kind, table, op[2], copy.deepcopy(op[3])))
            elif kind == "delete":
                prepared.append((kind, table, op[2], None))
            elif kind == "append":
                if not isinstance(self._data[table], list):
                    raise ValueError(f"cannot append to {table!r}")
                prepared.append((kind, table, None, copy.deepcopy(op[2])))
            else:
                raise ValueError(f"unknown store operation {kind!r}")
        for kind, table, key, value in prepared:  # plain dict/list operations: cannot fail half-way
            if kind == "set":
                self._data[table][key] = value
            elif kind == "delete":
                self._data[table].pop(key, None)
            else:
                self._data[table].append(value)
        self.writes += 1


def _is_timeout(exc):
    return "timeout" in type(exc).__name__.lower()


# --------------------------------------------------------------------------- app

class BillingApp:
    def __init__(self, gateway, store=None):
        if gateway is None:
            raise ValueError("a gateway is required")
        self.gateway = gateway
        if store is None:
            store = Store()
        if isinstance(store, Store):
            self._db = store
        else:  # any object with fail_next_write: it controls failures, data lives in an internal Store (D12)
            self._db = Store(flag_source=store)
        self.store = store
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ orders (M01)

    def _get(self, order_id):
        o = self._db.get("orders", order_id)
        if o is None:
            raise OrderNotFound(order_id)
        return o

    @staticmethod
    def _check_transition(order, new_status):
        if new_status not in TRANSITIONS[order["status"]]:
            raise InvalidState(f"order {order['id']} cannot go from {order['status']} to {new_status}")

    @staticmethod
    def _check_amount(amount_cents):
        if isinstance(amount_cents, bool) or not isinstance(amount_cents, int) or amount_cents <= 0:
            raise ValueError("amount_cents must be a positive integer number of cents")

    def _new_order_ops(self, customer, amount_cents):
        if customer is None:
            raise ValueError("customer is required")
        self._check_amount(amount_cents)
        seq = self._db.get("meta", "seq") + 1
        order_id = f"ord_{seq}"
        order = {"id": order_id, "customer": customer, "amount_cents": amount_cents,
                 "status": PENDING, "charge_id": None}
        return order_id, [("set", "meta", "seq", seq), ("set", "orders", order_id, order)]

    def create_order(self, customer, amount_cents):
        with self._lock:
            order_id, ops = self._new_order_ops(customer, amount_cents)
            self._db.write(ops)
            return order_id

    def order(self, order_id):
        with self._lock:
            o = self._get(order_id)
            return {"status": o["status"], "amount_cents": o["amount_cents"], "charge_id": o["charge_id"]}

    def ledger(self):
        with self._lock:
            return [dict(e) for e in self._db.all("ledger")]

    @staticmethod
    def _entry(order, kind):
        return ("append", "ledger", {"order_id": order["id"], "kind": kind, "amount_cents": order["amount_cents"]})

    # ------------------------------------------------------------------ payments (M02)

    def pay(self, order_id, key):
        """Charge the order once. Retrying with the same key (or any key) never charges twice.

        Returns the charge id. Raises the gateway's error (for example GatewayTimeout) if the gateway
        fails; the order then stays pending with its attempt recorded, and a retry collects the
        original charge through the gateway's idempotency key.
        """
        if key is None or key == "":
            raise ValueError("an idempotency key is required")
        with self._lock:
            o = self._get(order_id)
            owner = self._db.get("keys", key)
            if owner is not None and owner != order_id:
                raise IdempotencyKeyReused(f"key {key!r} was already used for order {owner}")
            if o["status"] == PAID:
                return o["charge_id"]  # already paid: never charge again
            if o["status"] != PENDING:
                raise InvalidState(f"order {order_id} is {o['status']} and cannot be paid")

            gateway_key = self._db.get("order_keys", order_id)
            ops = []
            if owner is None:
                ops.append(("set", "keys", key, order_id))
            if gateway_key is None:
                gateway_key = key
                ops.append(("set", "order_keys", order_id, key))
            if ops:
                self._db.write(ops)  # record the attempt before money moves

            charge_id = self.gateway.charge(o["amount_cents"], gateway_key)  # errors propagate; attempt kept

            o = self._get(order_id)  # a webhook cannot interleave (lock), but re-read for safety
            if o["status"] == PAID:
                return o["charge_id"]
            if o["status"] == CANCELLED:  # cannot happen under the lock; refund rather than keep money
                self._late_charge(o, charge_id, extra_ops=[])
                return charge_id
            self._check_transition(o, PAID)
            o["status"], o["charge_id"] = PAID, charge_id
            self._db.write([("set", "orders", order_id, o), self._entry(o, "charge")])
            return charge_id

    # ------------------------------------------------------------------ refunds and cancel (M04)

    def cancel(self, order_id):
        """pending -> cancelled; paid -> refunded (one gateway refund); otherwise no change.

        Returns the order's status afterwards.
        """
        with self._lock:
            o = self._get(order_id)
            record = self._db.get("refunds", order_id)
            if record is not None and o["status"] != REFUNDED:
                return self._finish_refund(o, record)  # a refund was already requested: never call again
            if o["status"] == PENDING:
                self._check_transition(o, CANCELLED)
                o["status"] = CANCELLED
                self._db.write([("set", "orders", order_id, o)])
                return CANCELLED
            if o["status"] == PAID:
                return self._refund(o, extra_ops=[])
            return o["status"]  # cancelled or refunded: nothing to do, never refund again

    def _refund(self, o, extra_ops):
        """Refund a charged order exactly once. extra_ops are written with the refund record."""
        record = {"charge_id": o["charge_id"], "state": "requested", "refund_id": None}
        self._db.write(list(extra_ops) + [("set", "refunds", o["id"], record)])  # before the gateway call
        try:
            refund_id = self.gateway.refund(o["charge_id"])
        except Exception as exc:
            if _is_timeout(exc):
                # outcome unknown: keep the record so the gateway is never asked again (no double refund)
                raise RefundOutcomeUnknown(
                    f"refund of {o['id']} timed out; it will be completed without a second refund") from exc
            self._db.write([("delete", "refunds", o["id"])])  # known failure: allow a later attempt
            raise
        record["refund_id"] = refund_id
        return self._finish_refund(self._get(o["id"]), record)

    def _finish_refund(self, o, record):
        record = dict(record, state="done")
        self._check_transition(o, REFUNDED)
        o["status"] = REFUNDED
        self._db.write([("set", "orders", o["id"], o), ("set", "refunds", o["id"], record), self._entry(o, "refund")])
        return REFUNDED

    def _late_charge(self, o, charge_id, extra_ops):
        """A charge arrived for a cancelled order (D13): record it, then refund it once."""
        o["charge_id"] = charge_id
        ops = list(extra_ops) + [("set", "orders", o["id"], o), self._entry(o, "charge")]
        return self._refund(o, extra_ops=ops)

    # ------------------------------------------------------------------ webhooks (M03)

    def handle_webhook(self, event):
        """Apply a gateway event at most once. Returns True if it changed anything, else False."""
        if not isinstance(event, dict) or not event.get("id") or not event.get("type"):
            raise ValueError("a webhook event needs an id and a type")
        with self._lock:
            event_id = event["id"]
            if self._db.has("events", event_id):
                return False  # duplicate delivery
            seen = ("set", "events", event_id, event["type"])
            o = self._db.get("orders", event.get("order_id"))
            etype, charge_id = event["type"], event.get("charge_id")

            if o is not None and etype == "charge.succeeded" and charge_id:
                if o["status"] == PENDING:
                    o["status"], o["charge_id"] = PAID, charge_id
                    self._db.write([seen, ("set", "orders", o["id"], o), self._entry(o, "charge")])
                    return True
                if o["status"] == CANCELLED and o["charge_id"] is None and not self._db.has("refunds", o["id"]):
                    self._late_charge(o, charge_id, extra_ops=[seen])
                    return True
            elif o is not None and etype == "charge.refunded":
                matches = charge_id is None or charge_id == o["charge_id"]
                if o["status"] in (PAID, CANCELLED) and o["charge_id"] and matches:
                    record = self._db.get("refunds", o["id"]) or {"charge_id": o["charge_id"], "refund_id": None}
                    record = dict(record, state="done")
                    self._check_transition(o, REFUNDED)
                    o["status"] = REFUNDED
                    self._db.write([seen, ("set", "orders", o["id"], o), ("set", "refunds", o["id"], record),
                                    self._entry(o, "refund")])
                    return True
            # unknown order, unknown type, or nothing to change: remember the id so it is never re-applied
            self._db.write([seen])
            return False

    # ------------------------------------------------------------------ subscriptions (M05)

    def renew(self, subscription, period=None):
        """Create the order for one subscription renewal (Subscribe's renew, adapted).

        With a period (and a subscription "id"), renewing the same period again returns the same order.
        """
        with self._lock:
            customer, price = subscription["customer"], subscription["price"]
            if period is None:
                return self.create_order(customer, price)
            if subscription.get("id") is None:
                raise ValueError("a subscription id is needed to renew by period")
            renewal_key = f"{subscription['id']!r}|{period!r}"
            existing = self._db.get("renewals", renewal_key)
            if existing is not None:
                return existing
            order_id, ops = self._new_order_ops(customer, price)
            self._db.write(ops + [("set", "renewals", renewal_key, order_id)])
            return order_id


def create_app(gateway, store=None):
    """Create the billing app around a payment gateway and an optional store."""
    return BillingApp(gateway, store)
