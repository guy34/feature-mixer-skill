def pay(gateway, order, key=None):
    order["charge_id"] = gateway.charge(order["amount"], key or str(id(order)))
    order["paid"] = True
def on_webhook(order, event):
    order["paid"] = True          # every delivery applies again
