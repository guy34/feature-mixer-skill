import os
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.dirname(APP)  # gateway.py (the task's mock gateway) lives next to app/
for p in (APP, RUN):
    if p not in sys.path:
        sys.path.insert(0, p)

import gateway  # noqa: E402
from unified import billing  # noqa: E402


def make(store=None):
    gw = gateway.FakeGateway()
    return gw, billing.create_app(gw, store=store)
