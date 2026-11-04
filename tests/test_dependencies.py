"""Dependency compatibility: versions, runtimes, frameworks, duplicate libraries, module cycles."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import Workspace, run_script  # noqa: E402

import check_dependencies as cd  # noqa: E402


def make_app(root, name, package=None, requirements=None, runtime=None):
    path = os.path.join(root, name)
    os.makedirs(path)
    if package is not None:
        with open(os.path.join(path, "package.json"), "w") as f:
            json.dump(package, f)
    if requirements is not None:
        with open(os.path.join(path, "requirements.txt"), "w") as f:
            f.write(requirements)
    if runtime is not None:
        with open(os.path.join(path, "runtime.txt"), "w") as f:
            f.write(runtime)
    return path


def kinds(conflicts):
    return {(c["kind"], c["subject"]): c for c in conflicts}


class DependencyAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = cls.tmp.name
        cls.a = make_app(root, "a", {"dependencies": {"react": "^18.2.0", "express": "^4.18.2", "axios": "^1.6.0",
                                                      "dayjs": "^1.11.0"},
                                     "devDependencies": {"jest": "^29.0.0"}, "engines": {"node": ">=18"}})
        cls.b = make_app(root, "b", {"dependencies": {"react": "^17.0.2", "express": "4.x", "node-fetch": "^2.6.0",
                                                      "moment": "^2.29.0"},
                                     "devDependencies": {"jest": "^29.7.0"}, "engines": {"node": "16.x"}})
        cls.c = make_app(root, "c", requirements="flask==3.0.0\nrequests>=2.31  # http\n-r base.txt\n",
                         runtime="python-3.11")
        os.makedirs(os.path.join(cls.a, "node_modules", "left-pad"))
        with open(os.path.join(cls.a, "node_modules", "left-pad", "package.json"), "w") as f:
            json.dump({"dependencies": {"react": "^16.0.0"}}, f)
        cls.stacks = {"A": cd.scan_manifests(cls.a), "B": cd.scan_manifests(cls.b), "C": cd.scan_manifests(cls.c)}
        cls.found = kinds(cd.analyse(cls.stacks))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_scan_reads_manifests_and_skips_node_modules(self):
        self.assertEqual(self.stacks["A"]["packages"]["react"], "^18.2.0")
        self.assertEqual(self.stacks["C"]["packages"]["flask"], "==3.0.0")
        self.assertEqual(self.stacks["C"]["runtimes"]["python"], "3.11")
        self.assertEqual(self.stacks["B"]["runtimes"]["node"], "16.x")

    def test_framework_version_conflict_is_high(self):
        c = self.found[("version", "react")]
        self.assertEqual(c["severity"], "high")
        self.assertEqual(c["apps"], ["A", "B"])

    def test_same_major_is_not_a_conflict(self):
        self.assertNotIn(("version", "express"), self.found)
        self.assertNotIn(("version", "jest"), self.found)

    def test_runtime_conflict(self):
        self.assertEqual(self.found[("runtime", "node")]["severity"], "high")

    def test_mixed_runtimes(self):
        c = self.found[("runtime-mix", "backend-runtime")]
        self.assertIn("node: A, B", c["detail"])
        self.assertIn("python: C", c["detail"])

    def test_framework_conflict(self):
        c = self.found[("framework", "backend-framework")]
        self.assertIn("Express (A, B)", c["detail"])
        self.assertIn("Flask (C)", c["detail"])
        self.assertIn("Express is used by the most sources", c["recommended"])

    def test_duplicate_libraries(self):
        self.assertEqual(self.found[("duplicate-library", "http-client")]["severity"], "low")
        self.assertIn(("duplicate-library", "date-library"), self.found)

    def test_version_rules(self):
        self.assertFalse(cd.versions_conflict("^18.2.0", "18.x"))
        self.assertTrue(cd.versions_conflict("^17.0.2", "~18.1"))
        self.assertFalse(cd.versions_conflict(">=16", "^18.0.0"))
        self.assertTrue(cd.versions_conflict(">=18", "16.x"))
        self.assertIsNone(cd.versions_conflict("latest", "^1.0.0"))
        self.assertIsNone(cd.versions_conflict("git+https://example.com/x.git", "1.0.0"))

    def test_cli_scan(self):
        r = run_script("check_dependencies.py", "--scan", f"A={self.a}", "--scan", f"B={self.b}")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("[high] dependency:version:react", r.stdout)
        strict = run_script("check_dependencies.py", "--scan", f"A={self.a}", "--scan", f"B={self.b}", "--strict")
        self.assertEqual(strict.returncode, 1)


class ModuleCycleTest(unittest.TestCase):
    def test_circular_modules_block(self):
        ws = Workspace(apps=("A",))
        try:
            ws.write_json("compat/dependencies.json",
                          {"modules": {"tasks": ["notifications"], "notifications": ["approvals"],
                                       "approvals": ["tasks"], "accounts": []}})
            r = ws.run("check_dependencies.py")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("[critical] dependency:circular-module:approvals->tasks->notifications->approvals", r.stdout)
        finally:
            ws.close()

    def test_source_json_packages_used_for_closed_apps(self):
        ws = Workspace(apps=("A", "B"))
        try:
            from _helpers import source_json
            ws.set_source("A", source_json("A", packages={"vue": "^3.4.0"}))
            ws.set_source("B", source_json("B", packages={"react": "^18.2.0"}))
            r = ws.run("check_dependencies.py", "--json")
            data = json.loads(r.stdout)
            self.assertIn("dependency:framework:frontend-framework", [c["id"] for c in data["conflicts"]])
        finally:
            ws.close()


if __name__ == "__main__":
    unittest.main()
