# Unified Billing

Built by Feature Mixer from Billfold (charges, webhooks), Subscribe (renewals) and Orderly (order states).
Module: `unified/billing.py` (Python 3.8+, standard library only). Design: `../mixer/design/`.

Run the tests (needs `gateway.py` one folder up, the task's mock gateway):

    python3 -m unittest discover -s tests -t .
