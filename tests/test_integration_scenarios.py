"""Phase 4 (v2.2): integration scenarios J-O.

For each scenario this proves three things:
  1. its hidden conformance tests pass on a correct reference integration,
  2. they fail on a plausible naive merge, at the tests the answer key names (so they discriminate),
  3. check_compatibility.py, given what a correct recon would extract (sources.json), finds the conflicts the
     answer key lists and none it must not.
Whether an agent running Feature Mixer extracts those facts and builds a passing app is measured by the
benchmark runs (benchmarks/RESULTS.md), not here.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import ROOT, Workspace, source_json  # noqa: E402

import check_compatibility as cc  # noqa: E402

INTEGRATION = os.path.join(ROOT, "benchmarks", "integration")
KEYS = os.path.join(ROOT, "benchmarks", "answer-keys", "integration")
sys.path.insert(0, INTEGRATION)
import run_holdout  # noqa: E402

SCENARIOS = ["J-auth", "K-tenancy", "L-rules", "M-payments", "N-files", "O-api"]


def key(name):
    with open(os.path.join(KEYS, f"{name}.json")) as f:
        return json.load(f)


class ScenarioTest(unittest.TestCase):
    def check(self, name):
        folder = os.path.join(INTEGRATION, name)
        ref = run_holdout.run(folder, os.path.join(folder, "reference"))
        self.assertEqual(ref["status"], "ran", ref)
        self.assertEqual(ref["failed"], 0, {k: v for k, v in ref["tests"].items() if v["status"] != "passed"})
        naive = run_holdout.run(folder, os.path.join(folder, "naive"))
        failed = {k for k, v in naive["tests"].items() if v["status"] == "failed"}
        must = set(key(name)["holdout_must_fail_on_naive"])
        self.assertTrue(must <= failed, f"the naive merge passed {sorted(must - failed)}")
        self.compat(name)

    def compat(self, name):
        with open(os.path.join(INTEGRATION, name, "sources.json")) as f:
            data = json.load(f)
        apps = [a for a in data if len(a) == 1]
        ws = Workspace(apps=tuple(apps), format=3)
        self.addCleanup(ws.close)
        for a in apps:
            ws.set_source(a, source_json(a, **{k: v for k, v in data[a].items() if k != "app"}))
        if "architecture" in data:
            ws.write_json("design/architecture.json", data["architecture"])
        found = {(c["kind"], c["subject"]) for c in cc.run(ws.mixer, use_all=True)["conflicts"]}
        k = key(name)
        for c in k["conflicts"]:
            self.assertIn((c["kind"], c["subject"]), found, f"{name}: missed {c}")
        for c in k.get("must_not_find", []):
            self.assertNotIn((c["kind"], c["subject"]), found, f"{name}: false positive {c}")

    def test_J_authentication(self):
        self.check("J-auth")

    def test_K_tenant_isolation(self):
        self.check("K-tenancy")

    def test_L_business_rules(self):
        self.check("L-rules")

    def test_M_payments(self):
        self.check("M-payments")

    def test_N_file_storage(self):
        self.check("N-files")

    def test_O_api_integration(self):
        self.check("O-api")

    def test_runner_reports_a_missing_module_as_an_error_not_a_pass(self):
        folder = os.path.join(INTEGRATION, "J-auth")
        res = run_holdout.run(folder, os.path.join(INTEGRATION, "K-tenancy", "reference"))
        self.assertNotEqual(res.get("failed"), 0)
        self.assertFalse(res["status"] == "ran" and res.get("failed") == 0)


if __name__ == "__main__":
    unittest.main()
