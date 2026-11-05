"""Test-execution verification (v2.1): real runs, fabricated and tampered reports, regressions."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import Workspace, row, run_script  # noqa: E402

import verify_tests  # noqa: E402

TESTS = '''import unittest


class T(unittest.TestCase):
    def test_login(self):
        """features: M01
        acceptance: AC01
        expect: signing in works
        level: auth"""
        self.assertTrue(True)

    def test_tasks(self):
        """features: M02
        expect: tasks can be created"""
        self.assertEqual(1, {value})

    @unittest.skip("needs a browser")
    def test_ui(self):
        """features: M02"""
'''


class RunAndVerifyTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(apps=("A",), format=3)
        self.addCleanup(self.ws.close)
        self.ws.menu([row("M01", "Sign in"), row("M02", "Tasks", depends_on="M01")])
        self.app = os.path.join(self.ws.root, "app")
        os.makedirs(os.path.join(self.app, "tests"))
        open(os.path.join(self.app, "tests", "__init__.py"), "w").close()
        self.write_tests(value=2)  # test_tasks fails by default
        self.approval = self.ws.grant(self.app, unittest="tests")
        os.makedirs(os.path.join(self.ws.mixer, "design"))
        with open(os.path.join(self.ws.mixer, "design", "prd.md"), "w") as f:
            f.write("# PRD\n\n## Acceptance criteria\n\n| Id | Feature | Text |\n| --- | --- | --- |\n"
                    "| AC01 | M01 | sign in |\n| AC02 | M02 | tasks |\n\n## Out of scope\n")

    def write_tests(self, value):
        """value 1 makes test_tasks pass, anything else makes it fail."""
        with open(os.path.join(self.app, "tests", "test_app.py"), "w") as f:
            f.write(TESTS.replace("{value}", str(value)))

    def run_tests(self, *extra):
        return run_script("run_tests.py", "--mixer", self.ws.mixer, "--cwd", self.app, "--unittest", "tests",
                          "--approval", self.approval, *extra)

    def report(self):
        with open(os.path.join(self.ws.mixer, "integration-report.json")) as f:
            return json.load(f)

    def save_report(self, data):
        with open(os.path.join(self.ws.mixer, "integration-report.json"), "w") as f:
            json.dump(data, f)

    def verify(self):
        return verify_tests.verify(self.ws.mixer, {"M01", "M02"})

    def test_executed_passed_failed_skipped(self):
        r = self.run_tests()
        self.assertEqual(r.returncode, 1, r.stdout)
        rep = self.report()
        status = {t["name"].split(".")[-1]: t["status"] for t in rep["tests"]}
        self.assertEqual(status, {"test_login": "passed", "test_tasks": "failed", "test_ui": "skipped"})
        ex = rep["execution"]
        for key in ("run_id", "started_at", "finished_at", "exit_code", "log", "log_sha256", "results_sha256"):
            self.assertIn(key, ex)
        self.assertEqual(ex["exit_code"], 1)
        self.assertEqual(rep["framework"], "unittest")
        login = next(t for t in rep["tests"] if t["name"].endswith("test_login"))
        self.assertEqual((login["features"], login["acceptance"], login["level"]), (["M01"], ["AC01"], "auth"))
        v, result = self.verify()
        self.assertEqual(result["features"], {"M01": "verified", "M02": "failed"})
        self.assertIn("kept feature M02 has no passing test", "\n".join(v.errors))
        self.assertIn("acceptance criterion AC02 has no verified passing test", "\n".join(v.errors))

    def test_all_green_verifies(self):
        self.write_tests(value=1)
        with open(os.path.join(self.app, "tests", "test_app.py")) as f:
            text = f.read()
        text = text.replace('expect: tasks can be created"""', 'acceptance: AC02\n        expect: tasks can be created"""')
        with open(os.path.join(self.app, "tests", "test_app.py"), "w") as f:
            f.write(text)
        self.assertEqual(self.run_tests().returncode, 0)
        v, result = self.verify()
        self.assertEqual(v.errors, [])
        self.assertEqual(result["acceptance"], {"AC01": "verified", "AC02": "verified"})
        r = run_script("verify_tests.py", self.ws.mixer, "--update-baseline")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("baseline updated", r.stdout)

    def test_fabricated_pass_is_caught(self):
        self.run_tests()
        rep = self.report()
        for t in rep["tests"]:
            if t["name"].endswith("test_tasks"):
                t["status"], t["actual"] = "passed", "as expected"
                t.pop("error", None)
        rep["summary"].update(passed=2, failed=0)
        self.save_report(rep)
        v, result = self.verify()
        self.assertIn("is reported passed but the results file says failed", "\n".join(v.errors))
        self.assertEqual(result["features"]["M02"], "failed")

    def test_invented_test_is_unverified(self):
        self.run_tests()
        rep = self.report()
        rep["tests"].append({"name": "tests.test_app.T.test_imaginary", "features": ["M02"], "expected": "x",
                             "actual": "as expected", "status": "passed"})
        rep["summary"].update(total=4, passed=2)
        self.save_report(rep)
        v, result = self.verify()
        self.assertIn("test_imaginary is reported passed but is not in the results file", "\n".join(v.errors))
        self.assertEqual(result["tests"]["tests.test_app.T.test_imaginary"], "unverified")

    def test_tampered_log_and_missing_run_record(self):
        self.run_tests()
        rep = self.report()
        with open(os.path.join(self.ws.mixer, rep["execution"]["log"]), "a") as f:
            f.write("OK\n")
        v, result = self.verify()
        self.assertIn("does not match its recorded fingerprint", "\n".join(v.errors))
        self.assertTrue(all(s in ("unverified", "not-executed") for s in result["tests"].values()))
        os.remove(os.path.join(self.ws.mixer, "test-runs", rep["execution"]["run_id"], "run.json"))
        v, _ = self.verify()
        self.assertIn("run.json is missing", "\n".join(v.errors))

    def test_exit_code_must_agree(self):
        self.run_tests()
        rep = self.report()
        rec_path = os.path.join(self.ws.mixer, "test-runs", rep["execution"]["run_id"], "run.json")
        with open(rec_path) as f:
            rec = json.load(f)
        rec["exit_code"] = rep["execution"]["exit_code"] = 0
        with open(rec_path, "w") as f:
            json.dump(rec, f)
        self.save_report(rep)
        v, _ = self.verify()
        errs = "\n".join(v.errors)
        # editing run.json is caught by its ledger fingerprint before anything else is trusted
        self.assertIn("was changed after the ledger recorded it", errs)
        import run_tests
        verdict, why = run_tests.decide_verdict("exited", 0, "ok", {"executed": 2, "failed": 1, "unverified": 0})
        self.assertEqual(verdict, "failed")
        self.assertIn("exit code 0 although 1 test(s) failed", why)
        verdict, why = run_tests.decide_verdict("exited", 3, "ok", {"executed": 2, "failed": 0, "unverified": 0})
        self.assertEqual(verdict, "inconsistent")

    def test_self_reported_report_without_evidence(self):
        self.save_report({"app": "x", "command": "trust me", "summary": {"total": 1, "passed": 1, "failed": 0,
                                                                        "skipped": 0},
                          "tests": [{"name": "t", "features": ["M01", "M02"], "expected": "x", "actual": "x",
                                     "status": "pass"}]})
        v, result = self.verify()
        self.assertIn("no execution evidence", "\n".join(v.errors))
        self.assertEqual(result["tests"], {"t": "unverified"})
        self.assertIn("kept feature M01 has no passing test", "\n".join(v.errors))
        self.ws.project["format"] = 2
        self.ws.save()
        v2, result2 = self.verify()
        self.assertEqual(v2.errors, [])
        self.assertEqual(result2["features"]["M01"], "unverified")
        self.assertIn("passes only in a report without execution evidence", "\n".join(v2.warnings))

    def test_not_executed_tests_from_tags(self):
        tags = os.path.join(self.ws.root, "tags.json")
        with open(tags, "w") as f:
            json.dump({"expected_tests": ["tests.test_app.T.test_export"],
                       "tests": {"tests.test_app.T.test_export": {"features": ["M02"]}}}, f)
        r = self.run_tests("--tags", tags)
        self.assertEqual(r.returncode, 1)
        rep = self.report()
        self.assertEqual(rep["summary"]["not_executed"], 1)
        v, result = self.verify()
        self.assertEqual(result["tests"]["tests.test_app.T.test_export"], "not-executed")
        self.assertIn("test_export did not run", "\n".join(v.errors))

    def test_regression_against_baseline(self):
        self.run_tests()
        rep = self.report()
        base = {"run_id": "old", "tests": {t["name"]: "passed" for t in rep["tests"]}}
        with open(os.path.join(self.ws.mixer, "test-baseline.json"), "w") as f:
            json.dump(base, f)
        v, _ = self.verify()
        errs = "\n".join(v.errors)
        self.assertIn("regression: tests.test_app.T.test_tasks passed in the baseline but is now failed", errs)
        self.assertIn("regression: tests.test_app.T.test_ui passed in the baseline but is now skipped", errs)

    def test_rerun_detects_changed_behaviour(self):
        self.write_tests(value=1)
        with open(os.path.join(self.app, "tests", "test_app.py")) as f:
            good = f.read()
        self.run_tests()
        with open(os.path.join(self.app, "tests", "test_app.py"), "w") as f:
            f.write(good.replace("self.assertTrue(True)", "self.assertTrue(False)"))
        r = run_script("verify_tests.py", self.ws.mixer, "--rerun")
        self.assertIn("rerun: tests.test_app.T.test_login was reported passed but the re-run gives failed", r.stdout)

    def test_junit_mode_any_framework(self):
        writer = os.path.join(self.app, "fake_runner.py")
        with open(writer, "w") as f:
            f.write("import sys\nopen('junit.xml','w').write('<testsuite><testcase classname=\"api\" name=\"t1\"/>"
                    "<testcase classname=\"api\" name=\"t2\"><error message=\"boom\"/></testcase></testsuite>')\n"
                    "sys.exit(1)\n")
        tags = os.path.join(self.ws.root, "tags.json")
        with open(tags, "w") as f:
            json.dump({"tests": {"api.t1": {"features": ["M01"], "level": "api"}, "t2": {"features": ["M02"]}}}, f)
        cmd = [sys.executable, "fake_runner.py"]
        aid = self.ws.grant(self.app, junit="junit.xml", command=cmd)
        r = run_script("run_tests.py", "--mixer", self.ws.mixer, "--cwd", self.app, "--junit", "junit.xml",
                       "--framework", "custom", "--tags", tags, "--approval", aid, "--", *cmd)
        self.assertEqual(r.returncode, 1, r.stdout)
        rep = self.report()
        self.assertEqual({t["name"]: t["status"] for t in rep["tests"]}, {"api.t1": "passed", "api.t2": "failed"})
        self.assertEqual(rep["tests"][0]["level"], "api")
        _, result = self.verify()
        self.assertEqual(result["features"], {"M01": "verified", "M02": "failed"})

    def test_stale_junit_file_is_refused(self):
        with open(os.path.join(self.app, "old.xml"), "w") as f:
            f.write("<testsuite><testcase name='t'/></testsuite>")
        os.utime(os.path.join(self.app, "old.xml"), (1, 1))
        cmd = [sys.executable, "-c", "pass"]
        aid = self.ws.grant(self.app, junit="old.xml", command=cmd)
        r = run_script("run_tests.py", "--mixer", self.ws.mixer, "--cwd", self.app, "--junit", "old.xml",
                       "--approval", aid, "--", *cmd)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("verdict invalid-results", r.stdout)
        self.assertIn("did not write old.xml during this run (an older copy was moved aside first)", r.stdout)
        rep = self.report()
        self.assertEqual(rep["summary"]["verdict"], "invalid-results")
        self.assertTrue(os.path.exists(os.path.join(self.ws.mixer, rep["execution"]["results"])))
        moved = [n for n in os.listdir(os.path.join(self.ws.mixer, "test-runs", rep["execution"]["run_id"]))
                 if n.startswith("previous-")]
        self.assertEqual(moved, ["previous-old.xml"])
        self.assertFalse(os.path.exists(os.path.join(self.app, "old.xml")))

    def test_project_requires_the_test_approval(self):
        self.write_tests(value=1)
        self.run_tests()
        rep = self.report()
        rep["execution"]["approval"] = "A09"
        self.save_report(rep)
        import validate_project
        msg = "\n".join(validate_project.check_test_approval(self.ws.mixer, self.ws.project).errors)
        self.assertIn("cites approval A09, which is not in project.json", msg)
        self.ws.approve("A09", "run-tests", "app suite")
        self.assertEqual(validate_project.check_test_approval(self.ws.mixer, self.ws.project).errors, [])


if __name__ == "__main__":
    unittest.main()
