def renew(subscription, create_order):
    return create_order(subscription["customer"], subscription["price"])
