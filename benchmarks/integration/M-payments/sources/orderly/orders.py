STATES = ("pending", "paid", "cancelled", "refunded")
def cancel(order):
    order["status"] = "cancelled"   # a paid order is cancelled without a refund
