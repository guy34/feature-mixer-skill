#!/usr/bin/env python3
"""Run a scenario's hidden conformance tests against an implementation of its interface.

Usage:
    python3 benchmarks/integration/run_holdout.py benchmarks/integration/M-payments IMPL_DIR [--json]

IMPL_DIR holds the module the scenario's task.md asks for (identity.py, tenancy.py, documents.py, billing.py,
files.py or contacts.py), for example a Feature Mixer run's app/unified folder, or the scenario's reference/
or naive/ folder. The tests import it with IMPL_DIR and the scenario folder (for gateway.py, transport.py)
on the path, in a separate interpreter with a timeout.

This executes the implementation: for an agent's output, run it only with the operator's approval, ideally
in a container. Standard library only.
"""

import argparse
import json
import os
import subprocess
import sys

RUNNER = r'''
import json, sys, unittest
sys.path[:0] = [sys.argv[1], sys.argv[2]]
suite = unittest.defaultTestLoader.discover(sys.argv[3], top_level_dir=sys.argv[3])
rows = []
class R(unittest.TextTestResult):
    def addSuccess(self, t): super().addSuccess(t); rows.append((t.id(), "passed", ""))
    def addFailure(self, t, e): super().addFailure(t, e); rows.append((t.id(), "failed", self._exc_info_to_string(e, t)[-400:]))
    def addError(self, t, e): super().addError(t, e); rows.append((t.id(), "failed", self._exc_info_to_string(e, t)[-400:]))
    def addSkip(self, t, r): super().addSkip(t, r); rows.append((t.id(), "skipped", r))
unittest.TextTestRunner(resultclass=R, stream=open("/dev/null" if sys.platform != "win32" else "nul", "w")).run(suite)
print("@@RESULTS@@" + json.dumps(rows))
'''


def run(scenario, impl, timeout=120):
    scenario, impl = os.path.abspath(scenario), os.path.abspath(impl)
    holdout = os.path.join(scenario, "holdout")
    try:
        p = subprocess.run([sys.executable, "-c", RUNNER, impl, scenario, holdout], capture_output=True, text=True,
                           timeout=timeout, cwd=impl)
    except subprocess.TimeoutExpired:
        return {"status": "timed-out", "tests": {}}
    marker = [line for line in p.stdout.splitlines() if line.startswith("@@RESULTS@@")]
    if not marker:
        return {"status": "error", "tests": {}, "stderr": p.stderr[-2000:]}
    rows = json.loads(marker[-1][len("@@RESULTS@@"):])
    tests = {tid.rsplit(".", 1)[-1]: {"status": st, "detail": msg} for tid, st, msg in rows}
    executed = [t for t in tests.values() if t["status"] != "skipped"]
    return {"status": "ran" if executed else "no-tests", "tests": tests,
            "passed": sum(t["status"] == "passed" for t in tests.values()),
            "failed": sum(t["status"] == "failed" for t in tests.values()), "total": len(tests)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run a scenario's hidden tests against an implementation.")
    ap.add_argument("scenario")
    ap.add_argument("impl")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = run(a.scenario, a.impl)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        for name, t in sorted(res["tests"].items()):
            print(f"{t['status']:<8} {name}")
        print(f"{res.get('passed', 0)} of {res.get('total', 0)} passed ({res['status']})")
    return 0 if res["status"] == "ran" and not res.get("failed") else 1


if __name__ == "__main__":
    sys.exit(main())
