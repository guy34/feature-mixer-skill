class GatewayTimeout(Exception):
    pass


class FakeGateway:
    """A mock payment gateway. Charges are idempotent by key, like real gateways' Idempotency-Key header."""

    def __init__(self):
        self.charges, self.refunds, self.by_key = {}, [], {}
        self.timeout_after_success = False

    def charge(self, amount_cents, key):
        if key in self.by_key:
            return self.by_key[key]
        cid = f"ch_{len(self.charges) + 1}"
        self.charges[cid] = amount_cents
        self.by_key[key] = cid
        if self.timeout_after_success:
            self.timeout_after_success = False
            raise GatewayTimeout("the charge went through but the response was lost")
        return cid

    def refund(self, charge_id):
        self.refunds.append(charge_id)
        return f"re_{len(self.refunds)}"
