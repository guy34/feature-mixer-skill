"""Unified Billing: orders, payments, webhooks, refunds, ledger and renewals.

Built by Feature Mixer from three sources (rebuilt, nothing copied):
  A Billfold  - charging through a gateway, gateway webhooks   (M01, M02)
  B Subscribe - subscription renewals that create orders       (M03)
  C Orderly   - order states and cancelling                     (M04, M05)
  new         - ledger, create/read orders (requested by the user) (M06, M07)

Public API (task.md):

    app = create_app(gateway, store=None)
    order_id = app.create_order(customer, amount_cents)
    app.pay(order_id, key)
    app.handle_webhook(event)
    app.cancel(order_id)
    app.order(order_id) -> {"status", "amount_cents", "charge_id"}
    app.ledger() -> [{"order_id", "kind", "amount_cents"}]
    app.renew(subscription, period) -> order_id

Guarantees (see mixer/design/architecture.md, decisions D03-D08):
  * one order produces at most one gateway charge, whatever keys are sent;
  * a webhook event id is applied at most once;
  * every state change is one atomic store write; a failed write raises
    StoreError and changes nothing; the intent of a gateway call is written
    before the call, so a failed write never leaves money moved without a
    record;
  * cancelling a paid order refunds it exactly once.

The module is one file with one section per architecture module (D02):
store, gateway-adapter, orders, ledger, payments, refunds, webhooks,
subscriptions, facade.
"""

import threading

__all__ = [
    "create_app", "BillingApp", "MemoryStore", "Store",
    "BillingError", "StoreError", "InvalidRequest", "UnknownOrder",
    "InvalidTransition", "IdempotencyConflict", "RefundPending",
    "STATES", "TRANSITIONS",
]


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------

class BillingError(Exception):
    """Base class for every error this module raises itself."""


class StoreError(BillingError):
    """A store write failed; nothing from that write was applied."""


class InvalidRequest(BillingError, ValueError):
    """The arguments are not acceptable (missing key, bad amount...)."""


class IdempotencyConflict(InvalidRequest):
    """An idempotency key that already belongs to another order."""


class UnknownOrder(BillingError, KeyError):
    """No order with this id."""

    def __str__(self):  # KeyError would show the repr of the args
        return Exception.__str__(self)


class InvalidTransition(BillingError):
    """The order's status does not allow this operation."""


class RefundPending(BillingError):
    """A refund was sent but its outcome is unknown; it is never re-sent
    automatically. The gateway's charge.refunded webhook completes it."""


# --------------------------------------------------------------------------
# store (module: store)
# --------------------------------------------------------------------------

class MemoryStore:
    """In-memory store whose writes are atomic batches.

    write(ops) applies every op or none. When ``fail_next_write`` is true on
    this store, or on the outside store object it was created for, the next
    write raises StoreError, applies nothing and clears the flag.
    """

    def __init__(self, control=None):
        self.fail_next_write = False
        self._control = control
        self.orders = {}
        self.ledger = []
        self.events = set()
        self.keys = {}
        self.renewals = {}

    def _take_failure(self):
        for holder in (self, self._control):
            if holder is not None and getattr(holder, "fail_next_write", False):
                try:
                    holder.fail_next_write = False
                except Exception:  # an object that will not let us reset it
                    pass
                return True
        return False

    def write(self, ops):
        """Apply a list of ops atomically: ("order", record), ("ledger",
        entry), ("event", event_id), ("key", key, order_id),
        ("renewal", renewal_key, order_id)."""
        if self._take_failure():
            raise StoreError("store write failed; nothing was changed")
        orders, ledger = dict(self.orders), list(self.ledger)
        events, keys, renewals = set(self.events), dict(self.keys), dict(self.renewals)
        for op in ops:
            kind = op[0]
            if kind == "order":
                orders[op[1]["id"]] = dict(op[1])
            elif kind == "ledger":
                ledger.append(dict(op[1]))
            elif kind == "event":
                events.add(op[1])
            elif kind == "key":
                keys[op[1]] = op[2]
            elif kind == "renewal":
                renewals[op[1]] = op[2]
            else:
                raise StoreError("unknown store operation %r; nothing was changed" % (kind,))
        self.orders, self.ledger = orders, ledger
        self.events, self.keys, self.renewals = events, keys, renewals


Store = MemoryStore


def _resolve_store(store):
    if store is None:
        return MemoryStore()
    if isinstance(store, MemoryStore):
        return store
    # Any other object (task.md: "an object with fail_next_write = False"):
    # keep the data here and honour that object's flag.
    return MemoryStore(control=store)


# --------------------------------------------------------------------------
# gateway adapter (module: gateway-adapter)
# --------------------------------------------------------------------------

def _is_timeout(exc):
    if isinstance(exc, TimeoutError):
        return True
    return any(cls.__name__ == "GatewayTimeout" for cls in type(exc).__mro__)


class _GatewayAdapter:
    def __init__(self, gateway, charge_attempts=2):
        self.gateway = gateway
        self.charge_attempts = charge_attempts

    def charge(self, amount_cents, key):
        """Charge with an idempotency key. A timeout is retried with the
        same key, which the gateway answers with the original charge
        instead of charging again (D06)."""
        for attempt in range(self.charge_attempts):
            try:
                return self.gateway.charge(amount_cents, key)
            except Exception as exc:
                if _is_timeout(exc) and attempt + 1 < self.charge_attempts:
                    continue
                raise

    def refund(self, charge_id):
        return self.gateway.refund(charge_id)


# --------------------------------------------------------------------------
# orders (module: orders; features M04, M07)
# --------------------------------------------------------------------------

STATES = ("pending", "paid", "cancelled", "refunded")
TRANSITIONS = {
    "pending": ("paid", "cancelled"),
    "paid": ("refunded",),
    "cancelled": ("refunded",),   # a late charge on a cancelled order, refunded (D07)
    "refunded": (),
}


def _moved(record, status, **changes):
    if status != record["status"] and status not in TRANSITIONS[record["status"]]:
        raise InvalidTransition("order %s cannot go from %s to %s"
                                % (record["id"], record["status"], status))
    new = dict(record)
    new.update(changes)
    new["status"] = status
    return new


def _view(record):
    return {"status": record["status"], "amount_cents": record["amount_cents"],
            "charge_id": record["charge_id"]}


def _check_amount(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InvalidRequest("%s must be a positive integer number of cents" % name)


def _check_customer(customer):
    if not isinstance(customer, str) or not customer.strip():
        raise InvalidRequest("customer must be a non-empty string")


def _check_text(value, name):
    if not isinstance(value, str) or not value:
        raise InvalidRequest("%s must be a non-empty string" % name)


def _ledger_entry(order_id, kind, amount_cents):
    return ("ledger", {"order_id": order_id, "kind": kind, "amount_cents": amount_cents})


# --------------------------------------------------------------------------
# facade (module: facade) with the payments, refunds, webhooks, ledger and
# subscriptions operations
# --------------------------------------------------------------------------

class BillingApp:
    def __init__(self, gateway, store=None):
        if gateway is None:
            raise InvalidRequest("a gateway is required")
        self.gateway = gateway
        self.store = store if store is not None else None
        self._store = _resolve_store(store)
        if self.store is None:
            self.store = self._store
        self._gw = _GatewayAdapter(gateway)
        self._lock = threading.RLock()

    # -- orders ------------------------------------------------------------

    def _get(self, order_id):
        try:
            record = self._store.orders.get(order_id)
        except TypeError:  # unhashable id
            record = None
        if record is None:
            raise UnknownOrder("unknown order %r" % (order_id,))
        return dict(record)

    def _new_order(self, customer, amount_cents):
        _check_customer(customer)
        _check_amount(amount_cents, "amount_cents")
        order_id = "ord_%d" % (len(self._store.orders) + 1)
        while order_id in self._store.orders:  # never reuse an id
            order_id += "_"
        return {"id": order_id, "customer": customer, "amount_cents": amount_cents,
                "status": "pending", "charge_id": None, "attempt_key": None,
                "refund_state": None, "refund_id": None}

    def create_order(self, customer, amount_cents):
        """M07: store a pending order; a failed write creates nothing."""
        with self._lock:
            record = self._new_order(customer, amount_cents)
            self._store.write([("order", record)])
            return record["id"]

    def order(self, order_id):
        """M07: {"status", "amount_cents", "charge_id"}."""
        with self._lock:
            return _view(self._get(order_id))

    # -- ledger (M06) --------------------------------------------------------

    def ledger(self):
        with self._lock:
            return [dict(e) for e in self._store.ledger]

    # -- payments (M01) ----------------------------------------------------

    def pay(self, order_id, key):
        """Charge the order once. Returns the charge id.

        The first attempt's key is written before the gateway is called and
        reused on every later attempt, so one order can only ever create one
        gateway charge; an order already paid is not charged again."""
        with self._lock:
            _check_text(key, "key (the client's idempotency key)")
            record = self._get(order_id)
            owner = self._store.keys.get(key)
            if owner is not None and owner != order_id:
                raise IdempotencyConflict("key already used for another order")
            if record["status"] == "paid":
                return record["charge_id"]
            if record["status"] != "pending":
                raise InvalidTransition("order %s is %s and cannot be paid"
                                        % (order_id, record["status"]))
            intent = []
            if record["attempt_key"] is None:
                record = dict(record, attempt_key=key)
                intent.append(("order", record))
            if owner is None:
                intent.append(("key", key, order_id))
            if intent:
                self._store.write(intent)  # StoreError here: nothing changed, nothing charged
            charge_id = self._gw.charge(record["amount_cents"], record["attempt_key"])
            paid = _moved(record, "paid", charge_id=charge_id)
            self._store.write([("order", paid),
                               _ledger_entry(order_id, "charge", record["amount_cents"])])
            return charge_id

    # -- refunds (M05) -----------------------------------------------------

    def cancel(self, order_id):
        """Cancel a pending order, or refund a paid one exactly once.
        Cancelling a cancelled or refunded order changes nothing.
        Returns the order view."""
        with self._lock:
            record = self._get(order_id)
            status = record["status"]
            if status == "pending":
                record = _moved(record, "cancelled")
                self._store.write([("order", record)])
            elif status == "paid":
                record = self._refund(record)
            return _view(record)

    def _refund(self, record):
        if record["refund_state"] == "requested":
            raise RefundPending("a refund for order %s was sent and its outcome is unknown; "
                                "it is not sent again" % record["id"])
        intent = dict(record, refund_state="requested")
        self._store.write([("order", intent)])  # StoreError here: nothing changed, nothing refunded
        refund_id = self._gw.refund(record["charge_id"])
        done = _moved(intent, "refunded", refund_state="done", refund_id=refund_id)
        self._store.write([("order", done),
                           _ledger_entry(record["id"], "refund", record["amount_cents"])])
        return done

    # -- webhooks (M02) ----------------------------------------------------

    def handle_webhook(self, event):
        """Apply a gateway event at most once (by event id)."""
        with self._lock:
            if not isinstance(event, dict):
                raise InvalidRequest("event must be a dict")
            event_id = event.get("id")
            _check_text(event_id, "event id")
            if event_id in self._store.events:
                return False
            done = ("event", event_id)
            kind, order_id = event.get("type"), event.get("order_id")
            record = self._store.orders.get(order_id) if isinstance(order_id, str) else None
            if record is None or kind not in ("charge.succeeded", "charge.refunded"):
                self._store.write([done])  # recorded and ignored
                return True
            record = dict(record)
            charge_id = event.get("charge_id")
            if kind == "charge.succeeded":
                self._charge_succeeded(record, charge_id, done)
            else:
                self._charge_refunded(record, charge_id, done)
            return True

    def _charge_succeeded(self, record, charge_id, done):
        status = record["status"]
        if status == "pending":
            paid = _moved(record, "paid", charge_id=charge_id or record["charge_id"])
            self._store.write([done, ("order", paid),
                               _ledger_entry(record["id"], "charge", record["amount_cents"])])
        elif status == "cancelled" and record["charge_id"] is None and charge_id:
            # Money arrived for an order cancelled while its payment was in
            # doubt: record the charge, then refund it once (D07).
            charged = dict(record, charge_id=charge_id)
            self._store.write([done, ("order", charged),
                               _ledger_entry(record["id"], "charge", record["amount_cents"])])
            self._refund(charged)
        else:  # already paid, refunded, or nothing to do
            self._store.write([done])

    def _charge_refunded(self, record, charge_id, done):
        matches = charge_id is None or charge_id == record["charge_id"]
        refundable = record["status"] in ("paid", "cancelled") and record["charge_id"] is not None
        if refundable and matches:
            refunded = _moved(record, "refunded", refund_state="done")
            self._store.write([done, ("order", refunded),
                               _ledger_entry(record["id"], "refund", record["amount_cents"])])
        else:
            self._store.write([done])

    # -- subscriptions (M03) -----------------------------------------------

    def renew(self, subscription, period):
        """Create the order for one subscription period, once. Renewing the
        same subscription for the same period returns the same order."""
        with self._lock:
            if not isinstance(subscription, dict):
                raise InvalidRequest("subscription must be a dict with id, customer, price_cents")
            sub_id = subscription.get("id")
            _check_text(sub_id, "subscription id")
            _check_text(period, "period")
            key = (sub_id, period)
            existing = self._store.renewals.get(key)
            if existing is not None:
                return existing
            record = self._new_order(subscription.get("customer"), subscription.get("price_cents"))
            self._store.write([("order", record), ("renewal", key, record["id"])])
            return record["id"]


def create_app(gateway, store=None):
    """Build the billing app around a gateway (gateway.FakeGateway() in
    tests) and an optional store (see MemoryStore)."""
    return BillingApp(gateway, store)
