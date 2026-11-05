"""Phase 1 (v2.2): approvals that bind to the exact run, timeouts, false-green reports, evidence integrity."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import SCRIPTS, Workspace, row, run_script  # noqa: E402

import verify_tests  # noqa: E402

POSIX = os.name != "nt"
GOOD = "import unittest\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        \"\"\"features: M01\"\"\"\n" \
       "        self.assertEqual(1, 1)\n"
BAD = GOOD.replace("assertEqual(1, 1)", "assertEqual(1, 2)")


def _put(path, text):
    with open(path, "w") as f:
        f.write(text)


def _put_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _get_json(path):
    with open(path) as f:
        return json.load(f)


def _get_text(path):
    with open(path) as f:
        return f.read()


def _get_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def junit_cmd(xml, exit_code=0, extra=""):
    code = f"open('junit.xml','w').write({xml!r}){extra}; import sys; sys.exit({exit_code})"
    return [sys.executable, "-c", code]


class Base(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(apps=("A",), format=3)
        self.addCleanup(self._cleanup)
        self.ws.menu([row("M01", "Sign in")])
        self.app = os.path.join(self.ws.root, "app")
        os.makedirs(os.path.join(self.app, "tests"))
        open(os.path.join(self.app, "tests", "__init__.py"), "w").close()
        self.write(GOOD)
        self.marker = os.path.join(self.ws.root, "ran.txt")

    def _cleanup(self):
        for base, dirs, files in os.walk(self.ws.root):
            for n in dirs + files:
                try:
                    os.chmod(os.path.join(base, n), 0o755)
                except OSError:
                    pass
        self.ws.close()

    def write(self, text, name="test_a.py"):
        with open(os.path.join(self.app, "tests", name), "w") as f:
            f.write(text)

    def run_unittest(self, approval, *extra):
        return run_script("run_tests.py", "--mixer", self.ws.mixer, "--cwd", self.app, "--unittest", "tests",
                          *(["--approval", approval] if approval else []), *extra)

    def run_cmd(self, cmd, approval, *extra, junit="junit.xml"):
        return run_script("run_tests.py", "--mixer", self.ws.mixer, "--cwd", self.app, "--junit", junit,
                          *(["--approval", approval] if approval else []), *extra, "--", *cmd)

    def marker_cmd(self):
        return [sys.executable, "-c", f"open({self.marker!r},'w').write('x'); "
                                      "open('junit.xml','w').write('<testsuite><testcase name=\"t\"/></testsuite>')"]

    def report(self):
        with open(os.path.join(self.ws.mixer, "integration-report.json")) as f:
            return json.load(f)

    def record(self):
        rep = self.report()
        with open(os.path.join(self.ws.mixer, "test-runs", rep["execution"]["run_id"], "run.json")) as f:
            return json.load(f)

    def log(self):
        path = os.path.join(self.ws.mixer, "approval-log.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(x) for x in f if x.strip()]

    def set_approval(self, aid, **changes):
        self.ws.reload()
        for a in self.ws.project["approvals"]:
            if a["id"] == aid:
                a.update(changes)
                for k, v in list(a.items()):
                    if v is None:
                        del a[k]
        self.ws.save()

    def verify_errors(self, **kw):
        rep, result = verify_tests.verify(self.ws.mixer, {"M01"}, **kw)
        return "\n".join(rep.errors), result


class ApprovalTest(Base):
    def refused(self, r):
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("refused:", r.stdout)
        self.assertIn("Nothing was run", r.stdout)
        self.assertFalse(os.path.exists(self.marker), "the command ran although it was refused")
        self.assertFalse(os.path.exists(os.path.join(self.ws.mixer, "integration-report.json")))
        last = self.log()[-1]
        self.assertEqual(last["decision"], "refused")
        return last["reason"]

    def test_missing_approval_runs_nothing(self):
        reason = self.refused(self.run_cmd(self.marker_cmd(), None))
        self.assertIn("no approval given", reason)

    def test_invented_approval_runs_nothing(self):
        self.assertIn("A77 is not in project.json", self.refused(self.run_cmd(self.marker_cmd(), "A77")))

    def test_approval_for_another_action(self):
        aid = self.ws.grant(self.app, command=self.marker_cmd(), action="migration")
        self.assertIn("is for 'migration', not 'run-tests'", self.refused(self.run_cmd(self.marker_cmd(), aid)))

    def test_approval_for_another_command(self):
        aid = self.ws.grant(self.app, command=[sys.executable, "-c", "print('the approved one')"])
        self.assertIn("covers a different command", self.refused(self.run_cmd(self.marker_cmd(), aid)))

    def test_approval_for_another_folder(self):
        other = os.path.join(self.ws.root, "other")
        os.makedirs(other)
        aid = self.ws.grant(other, command=self.marker_cmd())
        self.assertIn("covers the folder 'other', not 'app'", self.refused(self.run_cmd(self.marker_cmd(), aid)))

    def test_approval_for_another_junit_path_or_runner(self):
        aid = self.ws.grant(self.app, command=self.marker_cmd(), junit="other.xml")
        self.assertIn("results written to 'other.xml'", self.refused(self.run_cmd(self.marker_cmd(), aid)))
        aid = self.ws.grant(self.app, unittest="tests")
        self.assertIn("covers a unittest run, not a command run", self.refused(self.run_cmd(self.marker_cmd(), aid)))
        aid = self.ws.grant(self.app, unittest="other_tests")
        r = self.run_unittest(aid)
        self.assertEqual(r.returncode, 3)
        self.assertIn("unittest discovery in 'other_tests'", r.stdout)

    def test_expired_approval(self):
        aid = self.ws.grant(self.app, command=self.marker_cmd())
        self.set_approval(aid, expires_at="2020-01-01T00:00:00+00:00")
        self.assertIn("expired at 2020-01-01", self.refused(self.run_cmd(self.marker_cmd(), aid)))

    def test_single_use_approval_cannot_be_reused(self):
        aid = self.ws.grant(self.app, command=self.marker_cmd(), uses=1)
        self.assertEqual(self.run_cmd(self.marker_cmd(), aid).returncode, 0)
        os.remove(self.marker)
        self.assertIn("allowed 1 run(s) and has been used 1 time(s)",
                      self.refused_after_report(self.run_cmd(self.marker_cmd(), aid)))

    def refused_after_report(self, r):
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertFalse(os.path.exists(self.marker))
        return self.log()[-1]["reason"]

    def test_revoked_unapproved_unscoped_and_future_approvals(self):
        aid = self.ws.grant(self.app, command=self.marker_cmd())
        r = run_script("approvals.py", "revoke", "--mixer", self.ws.mixer, "--approval", aid, "--reason", "changed mind")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("was revoked", self.refused(self.run_cmd(self.marker_cmd(), aid)))
        aid2 = self.ws.grant(self.app, command=self.marker_cmd())
        self.set_approval(aid2, approved=False)
        self.assertIn("is not approved", self.refused(self.run_cmd(self.marker_cmd(), aid2)))
        self.ws.reload()
        self.ws.approve("A50", "run-tests", "app tests")  # a v2.1-style record: no scope
        self.assertIn("has no scope", self.refused(self.run_cmd(self.marker_cmd(), "A50")))
        aid3 = self.ws.grant(self.app, command=self.marker_cmd())
        self.set_approval(aid3, granted_at="2999-01-01T00:00:00+00:00")
        self.assertIn("granted in the future", self.refused(self.run_cmd(self.marker_cmd(), aid3)))

    def test_bound_approval_stops_when_code_changes(self):
        aid = self.ws.grant(self.app, unittest="tests", bind_code=True)
        self.assertEqual(self.run_unittest(aid).returncode, 0)
        self.write(GOOD + "\n# edited\n")
        r = self.run_unittest(aid)
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("have changed since", r.stdout)

    def test_valid_approval_runs_and_is_logged(self):
        aid = self.ws.grant(self.app, command=self.marker_cmd())
        r = self.run_cmd(self.marker_cmd(), aid)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(os.path.exists(self.marker))
        kinds = [e["decision"] for e in self.log()]
        self.assertEqual(kinds, ["granted", "accepted"])
        self.assertEqual(self.record()["approval"], aid)

    def test_grant_needs_user_confirmation(self):
        r = run_script("approvals.py", "grant", "--mixer", self.ws.mixer, "--cwd", self.app, "--unittest", "tests",
                       "--granted-by", "someone")
        self.assertEqual(r.returncode, 1)
        self.assertIn("--user-confirmed", r.stdout)
        self.ws.reload()
        self.assertEqual(self.ws.project["approvals"], [])

    def test_request_shows_the_exact_scope(self):
        r = run_script("approvals.py", "request", "--mixer", self.ws.mixer, "--cwd", self.app, "--junit", "j.xml",
                       "--", "pytest", "--junitxml=j.xml")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("the command pytest --junitxml=j.xml in app, writing j.xml", r.stdout)

    def test_audit_log_redacts_secrets_in_commands(self):
        token = "ghp_" + "S3cr3tT0k3n" * 4
        cmd = [sys.executable, "-c", "pass", "--password=hunter2hunter2", token, "postgres://u:pw12345@db/x"]
        self.run_cmd(cmd, None)
        aid = self.ws.grant(self.app, command=cmd)
        self.run_cmd(cmd, aid)
        dumped = _get_text(os.path.join(self.ws.mixer, "approval-log.jsonl")) + \
            _get_text(os.path.join(self.ws.mixer, "project.json"))
        for secret in ("hunter2hunter2", token, "pw12345"):
            self.assertNotIn(secret, dumped)
        rec = self.record()
        self.assertNotIn(token, json.dumps(rec))
        self.assertEqual(len(rec["argv_sha256"]), 64)

    def test_check_command_does_not_log_or_use(self):
        aid = self.ws.grant(self.app, unittest="tests", uses=1)
        r = run_script("approvals.py", "check", "--mixer", self.ws.mixer, "--approval", aid, "--cwd", self.app,
                       "--unittest", "tests")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.run_unittest(aid).returncode, 0)

    def test_rerun_needs_a_valid_approval(self):
        aid = self.ws.grant(self.app, unittest="tests", uses=1)
        self.assertEqual(self.run_unittest(aid).returncode, 0)
        marker = self.marker
        self.write(f"import unittest\nclass Y(unittest.TestCase):\n    def test_m(self):\n"
                   f"        open({marker!r},'w').write('x')\n", name="test_y.py")
        r = run_script("verify_tests.py", self.ws.mixer, "--rerun", "--no-write")
        self.assertIn("rerun: refused, nothing was run", r.stdout)
        self.assertFalse(os.path.exists(marker))
        fresh = self.ws.grant(self.app, unittest="tests", uses=1)
        r = run_script("verify_tests.py", self.ws.mixer, "--rerun", "--approval", fresh, "--no-write")
        self.assertTrue(os.path.exists(marker), r.stdout)


class TimeoutTest(Base):
    def test_hanging_command_is_stopped_and_recorded(self):
        cmd = [sys.executable, "-c", "import sys,time; print('started', flush=True); time.sleep(600)"]
        aid = self.ws.grant(self.app, command=cmd)
        t0 = time.time()
        r = self.run_cmd(cmd, aid, "--timeout", "2", "--kill-grace", "1")
        took = time.time() - t0
        self.assertLess(took, 15, "the run was not stopped near its timeout")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("timed_out", r.stdout)
        rec = self.record()
        self.assertEqual((rec["outcome"], rec["verdict"]), ("timed_out", "timed-out"))
        self.assertEqual(rec["timeout_seconds"], 2)
        self.assertIn("SIGTERM" if POSIX else "taskkill", rec["termination"]["signals"])
        with open(os.path.join(self.ws.mixer, rec["log"])) as f:
            self.assertIn("started", f.read())
        rep = self.report()
        self.assertEqual(rep["summary"]["verdict"], "timed-out")
        self.assertEqual(rep["summary"]["passed"], 0)
        errs, _ = self.verify_errors()
        self.assertIn("has verdict timed-out", errs)

    @unittest.skipUnless(POSIX, "process groups are POSIX")
    def test_grandchildren_are_terminated(self):
        pidfile = os.path.join(self.ws.root, "child.pid")
        code = ("import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(600)']);"
                f" open({pidfile!r},'w').write(str(p.pid)); time.sleep(600)")
        cmd = [sys.executable, "-c", code]
        aid = self.ws.grant(self.app, command=cmd)
        self.run_cmd(cmd, aid, "--timeout", "2", "--kill-grace", "1")
        with open(pidfile) as f:
            pid = int(f.read())
        self.assertFalse(_alive(pid), "the grandchild survived")

    @unittest.skipUnless(POSIX, "process groups are POSIX")
    def test_processes_left_after_a_normal_exit_are_terminated(self):
        pidfile = os.path.join(self.ws.root, "daemon.pid")
        code = ("import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(600)']);"
                f" open({pidfile!r},'w').write(str(p.pid)); "
                "open('junit.xml','w').write('<testsuite><testcase name=\"t\"/></testsuite>')")
        cmd = [sys.executable, "-c", code]
        aid = self.ws.grant(self.app, command=cmd)
        r = self.run_cmd(cmd, aid, "--kill-grace", "1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("still running after they finished", self.record()["termination"]["reason"])
        with open(pidfile) as f:
            self.assertFalse(_alive(int(f.read())))

    @unittest.skipUnless(POSIX, "signals are POSIX")
    def test_interruption_terminates_the_command_and_keeps_the_record(self):
        cmd = [sys.executable, "-c", "import time; print('working', flush=True); time.sleep(600)"]
        aid = self.ws.grant(self.app, command=cmd)
        proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "run_tests.py"), "--mixer", self.ws.mixer,
                                 "--cwd", self.app, "--junit", "junit.xml", "--approval", aid, "--kill-grace", "1",
                                 "--", *cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(2)
        proc.send_signal(signal.SIGTERM)
        out, _ = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 130, out)
        rec = self.record()
        self.assertEqual((rec["outcome"], rec["verdict"]), ("interrupted", "interrupted"))
        with open(os.path.join(self.ws.mixer, rec["log"])) as f:
            self.assertIn("working", f.read())

    def test_huge_output_is_capped_keeping_head_and_tail(self):
        code = ("import sys\nfor i in range(60000): print('line %06d ' % i + 'x' * 40)\nprint('THE-END')\n"
                "open('junit.xml','w').write('<testsuite><testcase name=\"t\"/></testsuite>')")
        cmd = [sys.executable, "-c", code]
        aid = self.ws.grant(self.app, command=cmd)
        r = self.run_cmd(cmd, aid, "--max-log-mb", "0.5")
        self.assertEqual(r.returncode, 0, r.stdout)
        rec = self.record()
        size = os.path.getsize(os.path.join(self.ws.mixer, rec["log"]))
        self.assertLess(size, 600 * 1024)
        self.assertGreater(rec["log_bytes_omitted"], 2_000_000)
        with open(os.path.join(self.ws.mixer, rec["log"])) as f:
            text = f.read()
        self.assertIn("line 000000", text)
        self.assertIn("THE-END", text)
        self.assertIn("bytes of output omitted by run_tests.py", text)

    def test_timeout_must_be_positive(self):
        aid = self.ws.grant(self.app, unittest="tests")
        r = self.run_unittest(aid, "--timeout", "0")
        self.assertEqual(r.returncode, 2)


def _alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().split()[2] != "Z"
    except OSError:
        return True


class FalseGreenTest(Base):
    def cmd_run(self, xml, exit_code=0, *extra):
        cmd = junit_cmd(xml, exit_code)
        aid = self.ws.grant(self.app, command=cmd)
        return self.run_cmd(cmd, aid, *extra)

    def test_zero_tests_is_never_success(self):
        self.write("# nothing\n")
        aid = self.ws.grant(self.app, unittest="tests")
        r = self.run_unittest(aid)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.record()["verdict"], "no-tests")
        errs, _ = self.verify_errors()
        self.assertIn("the report lists no tests", errs)
        self.assertIn("has verdict no-tests", errs)

    def test_all_skipped_is_never_success(self):
        self.write("import unittest\nclass T(unittest.TestCase):\n    @unittest.skip('later')\n"
                   "    def test_a(self):\n        pass\n")
        aid = self.ws.grant(self.app, unittest="tests")
        self.assertEqual(self.run_unittest(aid).returncode, 1)
        self.assertEqual(self.record()["verdict"], "no-tests")

    def test_exit_zero_with_failures_in_junit(self):
        r = self.cmd_run('<testsuite><testcase name="a"/><testcase name="b"><failure message="no"/></testcase>'
                         '</testsuite>', 0)
        self.assertEqual(r.returncode, 1)
        rec = self.record()
        self.assertEqual(rec["verdict"], "failed")
        self.assertIn("exit code 0 although 1 test(s) failed", rec["verdict_reasons"])
        errs, _ = self.verify_errors()
        self.assertIn("exit code 0 but the results contain failures", errs)

    def test_nonzero_exit_without_failures_proves_nothing(self):
        r = self.cmd_run('<testsuite><testcase name="a"/></testsuite>', 4)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.record()["verdict"], "inconsistent")
        errs, result = self.verify_errors()
        self.assertIn("has verdict inconsistent", errs)
        self.assertEqual(result["tests"]["a"], "unverified")

    def test_malformed_junit_replaces_an_earlier_green_report(self):
        self.cmd_run('<testsuite><testcase name="a"/></testsuite>')
        self.assertNotIn("has verdict", self.verify_errors()[0])
        self.cmd_run('<testsuite><testcase name=')
        rep = self.report()
        self.assertEqual(rep["summary"]["verdict"], "invalid-results")
        self.assertEqual(rep["tests"], [])
        errs, _ = self.verify_errors()
        self.assertIn("results file cannot be used", errs)

    def test_suite_totals_must_match_cases(self):
        self.cmd_run('<testsuite tests="3" failures="2"><testcase name="a"/></testsuite>')
        rec = self.record()
        self.assertEqual(rec["results_status"], "inconsistent")
        self.assertEqual(rec["verdict"], "inconsistent")
        self.assertIn("suite (unnamed suite) says tests=3 but lists 1", rec["results_problems"])
        errs, _ = self.verify_errors()
        self.assertIn("contradicts itself", errs)

    def test_unknown_result_elements_are_unverified(self):
        self.cmd_run('<testsuite><testcase name="a"><flakyFailure message="x"/></testcase></testsuite>')
        rec = self.record()
        self.assertEqual(rec["verdict"], "inconsistent")
        self.assertEqual(self.report()["tests"][0]["status"], "unverified")

    def test_oversized_results_are_not_read(self):
        cmd = [sys.executable, "-c", "open('junit.xml','w').write('<testsuite><testcase name=\"t\"/><!--' + "
               "'x' * 1200000 + '--></testsuite>')"]
        aid = self.ws.grant(self.app, command=cmd)
        self.run_cmd(cmd, aid, "--max-results-mb", "1")
        self.assertEqual(self.record()["verdict"], "invalid-results")
        self.assertEqual(self.record()["results_status"], "too-large")

    def test_expected_test_count(self):
        aid = self.ws.grant(self.app, unittest="tests")
        r = self.run_unittest(aid, "--expect-tests", "5")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.record()["verdict"], "incomplete")

    def test_failing_test_left_out_of_the_report(self):
        self.write(GOOD + "\n    def test_b(self):\n        self.fail('boom')\n")
        aid = self.ws.grant(self.app, unittest="tests")
        self.run_unittest(aid)
        path = os.path.join(self.ws.mixer, "integration-report.json")
        rep = self.report()
        rep["tests"] = [t for t in rep["tests"] if not t["name"].endswith("test_b")]
        rep["summary"].update(total=1, failed=0)
        with open(path, "w") as f:
            json.dump(rep, f)
        errs, _ = self.verify_errors()
        self.assertIn("test_b failed in the results file but is left out of the report", errs)

    def test_report_verdict_must_match_record(self):
        aid = self.ws.grant(self.app, unittest="tests")
        self.run_unittest(aid)
        rep = self.report()
        rep["execution"]["verdict"] = "passed"
        rep["execution"]["outcome"] = "timed_out"
        with open(os.path.join(self.ws.mixer, "integration-report.json"), "w") as f:
            json.dump(rep, f)
        errs, _ = self.verify_errors()
        self.assertIn("execution.outcome does not match the run record", errs)


class IntegrityTest(Base):
    def green(self, *extra):
        aid = self.ws.grant(self.app, unittest="tests")
        r = self.run_unittest(aid, *extra)
        self.assertEqual(r.returncode, 0, r.stdout)
        return aid

    def writable(self, path):
        os.chmod(path, 0o644)
        return path

    def test_clean_run_verifies_and_is_read_only(self):
        self.green()
        errs, result = self.verify_errors()
        self.assertNotIn("execution", errs)
        self.assertEqual(result["features"], {"M01": "verified"})
        rec = self.record()
        for name in ("run.json", "output.log", "results.xml"):
            mode = os.stat(os.path.join(self.ws.mixer, "test-runs", rec["run_id"], name)).st_mode & 0o777
            self.assertEqual(mode & 0o222, 0, f"{name} is writable")

    def test_each_file_tampered_alone(self):
        self.green()
        rec = self.record()
        run_dir = os.path.join(self.ws.mixer, "test-runs", rec["run_id"])
        for name, msg in (("results.xml", "results file"), ("output.log", "log file"),
                          ("run.json", "changed after the ledger recorded it")):
            path = self.writable(os.path.join(run_dir, name))
            original = _get_bytes(path)
            with open(path, "ab") as f:
                f.write(b"\n" if name != "run.json" else b" ")
            errs, result = self.verify_errors()
            self.assertIn(msg, errs, name)
            self.assertEqual(result["tests"], {t: "unverified" for t in result["tests"]})
            with open(path, "wb") as f:
                f.write(original)

    def forge_all(self):
        """Flip a failing run to green and rewrite results, run.json and the report consistently."""
        import hashlib
        rep = self.report()
        ex = rep["execution"]
        res = self.writable(os.path.join(self.ws.mixer, ex["results"]))
        text = _get_text(res)
        import re
        _put(res, re.sub(r"<failure[^>]*>.*?</failure>", "", text, flags=re.S).replace(
            'failures="1"', 'failures="0"'))
        rj = self.writable(os.path.join(self.ws.mixer, "test-runs", ex["run_id"], "run.json"))
        rec = _get_json(rj)
        rec["results_sha256"] = ex["results_sha256"] = hashlib.sha256(_get_bytes(res)).hexdigest()
        rec["exit_code"] = ex["exit_code"] = 0
        rec["verdict"] = ex["verdict"] = "passed"
        rec["counts"].update(passed=1, failed=0)
        rec["verdict_reasons"] = []
        _put_json(rj, rec)
        ex["run_record_sha256"] = hashlib.sha256(_get_bytes(rj)).hexdigest()
        for t in rep["tests"]:
            t.update(status="passed", actual="as expected")
            t.pop("error", None)
        rep["summary"].update(passed=1, failed=0, verdict="passed")
        _put_json(os.path.join(self.ws.mixer, "integration-report.json"), rep)
        return rec

    def rewrite_ledger(self):
        import hashlib
        path = self.writable(os.path.join(self.ws.mixer, "test-runs", "ledger.jsonl"))
        rows = [json.loads(x) for x in _get_text(path).splitlines()]
        prev = ""
        with open(path, "w") as f:
            for r in rows:
                rec = os.path.join(self.ws.mixer, "test-runs", r["run_id"], "run.json")
                r["run_record_sha256"] = hashlib.sha256(_get_bytes(rec)).hexdigest()
                r["prev"] = prev
                body = json.dumps({k: v for k, v in r.items() if k not in ("entry_sha256", "hmac")},
                                  sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                r["entry_sha256"] = hashlib.sha256(body.encode()).hexdigest()
                prev = r["entry_sha256"]
                f.write(json.dumps(r, sort_keys=True) + "\n")

    def test_consistent_forgery_is_caught_by_the_ledger(self):
        self.write(BAD)
        aid = self.ws.grant(self.app, unittest="tests")
        self.run_unittest(aid)
        self.forge_all()
        errs, _ = self.verify_errors()
        self.assertIn("changed after the ledger recorded it", errs)

    def test_full_rewrite_without_a_key_is_a_documented_limit(self):
        """A forger who rewrites the evidence, the report and the whole ledger is not detectable without a key."""
        self.write(BAD)
        aid = self.ws.grant(self.app, unittest="tests")
        self.run_unittest(aid)
        self.forge_all()
        self.rewrite_ledger()
        errs, result = self.verify_errors()
        self.assertNotIn("ledger", errs)
        self.assertEqual(result["features"], {"M01": "verified"})  # this is the limit SECURITY.md describes

    def test_full_rewrite_with_a_key_is_caught(self):
        keydir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, keydir)
        key = os.path.join(keydir, "evidence.key")
        _put(key, "k" * 40)
        self.write(BAD)
        aid = self.ws.grant(self.app, unittest="tests")
        self.run_unittest(aid, "--evidence-key", key)
        self.forge_all()
        self.rewrite_ledger()
        errs, _ = self.verify_errors(key_file=key)
        self.assertIn("signature", errs)
        wrong = os.path.join(keydir, "wrong.key")
        _put(wrong, "w" * 40)
        errs, _ = self.verify_errors(key_file=wrong)
        self.assertIn("different key", errs)

    def test_signed_run_verifies_with_its_key_and_key_must_be_outside_mixer(self):
        keydir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, keydir)
        key = os.path.join(keydir, "evidence.key")
        _put(key, "k" * 40)
        self.green("--evidence-key", key)
        errs, _ = self.verify_errors(key_file=key)
        self.assertNotIn("signature", errs)
        inside = os.path.join(self.ws.mixer, "evidence.key")
        _put(inside, "k" * 40)
        aid = self.ws.grant(self.app, unittest="tests")
        r = self.run_unittest(aid, "--evidence-key", inside)
        self.assertEqual(r.returncode, 2)
        self.assertIn("outside mixer/", r.stdout)

    def test_evidence_reused_from_another_workspace(self):
        self.green()
        other = Workspace(apps=("A",), format=3)
        self.addCleanup(other.close)
        other_app = os.path.join(other.root, "app")
        shutil.copytree(self.app, other_app)
        aid = other.grant(other_app, unittest="tests")
        run_script("run_tests.py", "--mixer", other.mixer, "--cwd", other_app, "--unittest", "tests",
                   "--approval", aid)
        rep = _get_json(os.path.join(other.mixer, "integration-report.json"))
        shutil.copytree(os.path.join(other.mixer, "test-runs", rep["execution"]["run_id"]),
                        os.path.join(self.ws.mixer, "test-runs", rep["execution"]["run_id"]))
        _put_json(os.path.join(self.ws.mixer, "integration-report.json"), rep)
        errs, _ = self.verify_errors()
        self.assertIn("is not in the run ledger", errs)

    def test_code_changed_after_the_run(self):
        self.green()
        self.write(GOOD + "\n# a later edit\n")
        errs, result = self.verify_errors()
        self.assertIn("changed after run", errs)
        self.assertEqual(result["features"]["M01"], "untested")

    def test_concurrent_run_is_refused_and_stale_lock_taken_over(self):
        lock = os.path.join(self.ws.mixer, "test-runs", ".lock")
        os.makedirs(os.path.dirname(lock), exist_ok=True)
        import socket
        _put_json(lock, {"pid": os.getpid(), "host": socket.gethostname(), "since": time.time()})
        aid = self.ws.grant(self.app, unittest="tests")
        r = self.run_unittest(aid)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("another test run", r.stdout)
        _put_json(lock, {"pid": 999999999, "host": socket.gethostname(), "since": time.time()})
        r = self.run_unittest(aid)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.record()["lock_taken_over"]["pid"], 999999999)
        self.assertFalse(os.path.exists(lock))

    def test_external_copy_is_compared(self):
        copies = tempfile.mkdtemp()
        self.addCleanup(lambda: (os.system(f"chmod -R u+w {copies}") if POSIX else None,
                                 shutil.rmtree(copies, ignore_errors=True)))
        self.green("--evidence-copy", copies)
        errs, _ = self.verify_errors(evidence_copy=copies)
        self.assertNotIn("copy", errs)
        rec = self.record()
        log_copy = os.path.join(copies, rec["run_id"], "output.log")
        os.chmod(log_copy, 0o644)
        with open(log_copy, "a") as f:
            f.write("x")
        errs, _ = self.verify_errors(evidence_copy=copies)
        self.assertIn("differs from the copy", errs)

    def test_ledger_entry_removed(self):
        self.green()
        self.green()
        path = self.writable(os.path.join(self.ws.mixer, "test-runs", "ledger.jsonl"))
        rows = _get_text(path).splitlines()
        _put(path, rows[1] + "\n")
        errs, _ = self.verify_errors()
        self.assertIn("removed or reordered", errs)


if __name__ == "__main__":
    unittest.main()
