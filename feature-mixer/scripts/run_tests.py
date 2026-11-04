#!/usr/bin/env python3
"""Run the unified app's tests and record evidence that they ran.

Usage (Python unittest, built-in harness):
    python3 run_tests.py --mixer mixer/ --cwd app/ --unittest tests [--top .]

Usage (any framework that writes JUnit XML: pytest, jest-junit, vitest, go-junit-report...):
    python3 run_tests.py --mixer mixer/ --cwd app/ --junit reports/junit.xml --framework pytest \
        [--tags tags.json] -- pytest --junitxml=reports/junit.xml

Optional: --approval A03 (the approval id in project.json for running these tests),
--no-report (record the run without rewriting the integration report).

What it records, in mixer/test-runs/<run-id>/:
  output.log    everything the command printed (stdout and stderr)
  results.xml   the per-test results (JUnit XML)
  run.json      command, framework, folder, start and finish times (UTC),
                exit code, and SHA-256 fingerprints of the log and results

Then it writes mixer/integration-report.json and .md from those files only.
Statuses: passed, failed, skipped, not-executed (a test the tags file
expects that did not run). Nothing is ever marked passed unless the results
file says so. verify_tests.py checks the report against this evidence later.

Test tags (which features a test proves) come from test docstrings in the
unittest harness ("features: M01, M04", "expect: ...", "level: ...",
"acceptance: AC01") or from a --tags JSON file:
    {"tests": {"<test id or name>": {"features": ["M01"], "expect": "...", "level": "api",
                                     "acceptance": ["AC01"]}},
     "expected_tests": ["<test id>", ...]}

This script executes the given command: run it only on code the user has
approved running. Exit codes: 0 every executed test passed, 1 failures or a
non-zero exit, 2 bad input or the command could not run.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

HARNESS = r'''
import os, re, sys, time, unittest
from xml.sax.saxutils import quoteattr, escape
start, top, out = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.path.abspath(top))

def tags(test):
    doc = getattr(test, "_testMethodDoc", None) or ""
    def grab(k):
        m = re.search(k + r":\s*(.+)", doc)
        return m.group(1).strip() if m else ""
    return {"features": grab("features"), "expect": grab("expect"), "level": grab("level"),
            "acceptance": grab("acceptance")}

class Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows, self.t0 = [], {}
    def startTest(self, t):
        self.t0[t.id()] = time.time()
        super().startTest(t)
    def _row(self, t, status, msg=""):
        self.rows.append((t, status, msg, time.time() - self.t0.get(t.id(), time.time())))
    def addSuccess(self, t):
        super().addSuccess(t); self._row(t, "passed")
    def addFailure(self, t, e):
        super().addFailure(t, e); self._row(t, "failed", self._exc_info_to_string(e, t))
    def addError(self, t, e):
        super().addError(t, e); self._row(t, "failed", self._exc_info_to_string(e, t))
    def addSkip(self, t, r):
        super().addSkip(t, r); self._row(t, "skipped", r)
    def addExpectedFailure(self, t, e):
        super().addExpectedFailure(t, e); self._row(t, "passed")
    def addUnexpectedSuccess(self, t):
        super().addUnexpectedSuccess(t); self._row(t, "failed", "unexpected success")

suite = unittest.defaultTestLoader.discover(start, top_level_dir=top)
res = unittest.TextTestRunner(resultclass=Result, verbosity=2, stream=sys.stdout).run(suite)
with open(out, "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<testsuite name="unittest" tests="%d">\n' % len(res.rows))
    for t, status, msg, dur in res.rows:
        cls, _, name = t.id().rpartition(".")
        f.write('  <testcase classname=%s name=%s time="%.3f">\n' % (quoteattr(cls), quoteattr(name), dur))
        f.write("    <properties>\n")
        for k, v in tags(t).items():
            if v:
                f.write("      <property name=%s value=%s/>\n" % (quoteattr(k), quoteattr(v)))
        f.write("    </properties>\n")
        if status == "failed":
            last = msg.strip().splitlines()[-1][:300] if msg.strip() else "failed"
            f.write("    <failure message=%s>%s</failure>\n" % (quoteattr(last), escape(msg[-3000:])))
        elif status == "skipped":
            f.write("    <skipped message=%s/>\n" % quoteattr(str(msg)[:300]))
        f.write("  </testcase>\n")
    f.write("</testsuite>\n")
sys.exit(0 if res.wasSuccessful() else 1)
'''


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def split_list(value):
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value or "").replace(";", ",").split(",") if v.strip()]


def parse_junit(path):
    """[{id, name, status, message, time, properties}] from a JUnit XML file."""
    root = ET.parse(path).getroot()
    out = []
    for case in root.iter("testcase"):
        cls, name = case.get("classname", ""), case.get("name", "")
        tid = f"{cls}.{name}" if cls else name
        status, message = "passed", ""
        for child in case:
            if child.tag in ("failure", "error"):
                status, message = "failed", child.get("message") or (child.text or "").strip()[:300]
            elif child.tag == "skipped":
                status, message = "skipped", child.get("message") or "skipped"
        props = {p.get("name"): p.get("value", "") for p in case.iter("property")}
        out.append({"id": tid, "name": name, "status": status, "message": message,
                    "time": case.get("time"), "properties": props})
    return out


def execute(mixer_dir, cwd, argv, framework, junit=None, unittest_start=None, top=".", approval=None,
            display_command=None):
    """Run the command, store the evidence, return the run record."""
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = os.path.join(mixer_dir, "test-runs", run_id)
    os.makedirs(run_dir)
    log_path = os.path.join(run_dir, "output.log")
    results_path = os.path.join(run_dir, "results.xml")
    if unittest_start:
        argv = [sys.executable, "-c", HARNESS, unittest_start, top, os.path.abspath(results_path)]
        display_command = display_command or f"python -m unittest discover -s {unittest_start} -t {top} " \
                                              "(Feature Mixer harness)"
        framework = "unittest"
    started_at = now()
    try:
        with open(log_path, "wb") as log:
            proc = subprocess.run(argv, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
        exit_code = proc.returncode
    except OSError as e:
        raise ValueError(f"could not run {argv[0]}: {e.strerror}")
    finished_at = now()
    if not unittest_start:
        src = junit if os.path.isabs(junit) else os.path.join(cwd, junit)
        if not os.path.exists(src):
            raise ValueError(f"the command did not write {junit}; no results to record (log: {log_path})")
        started_ts = datetime.fromisoformat(started_at).timestamp()
        if os.path.getmtime(src) < started_ts - 1:
            raise ValueError(f"{junit} is older than this run, so it is not this run's result")
        with open(src, "rb") as a, open(results_path, "wb") as b:
            b.write(a.read())
    if not os.path.exists(results_path):
        raise ValueError(f"no results file was produced (exit code {exit_code}); see {log_path}")
    record = {
        "run_id": run_id,
        "runner": "run_tests.py",
        "command": display_command or " ".join(argv),
        "argv": argv if not unittest_start else ["<harness>", unittest_start, top],
        "framework": framework,
        "cwd": os.path.relpath(os.path.abspath(cwd), os.path.dirname(os.path.abspath(mixer_dir))),
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
        "log": os.path.relpath(log_path, mixer_dir),
        "log_sha256": sha256(log_path),
        "results": os.path.relpath(results_path, mixer_dir),
        "results_sha256": sha256(results_path),
        "approval": approval,
        "unittest": {"start": unittest_start, "top": top} if unittest_start else None,
    }
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    return record


def build_report(mixer_dir, record, app_name, tags=None):
    tags = tags or {}
    by_test = tags.get("tests", {})
    results = parse_junit(os.path.join(mixer_dir, record["results"]))
    tests, seen = [], set()
    for r in results:
        seen.update({r["id"], r["name"]})
        t = by_test.get(r["id"]) or by_test.get(r["name"]) or {}
        p = r["properties"]
        actual = "as expected" if r["status"] == "passed" else (r["message"] or r["status"])
        row = {
            "name": r["id"],
            "level": t.get("level") or p.get("level") or "feature",
            "features": split_list(t.get("features") or p.get("features")),
            "acceptance": split_list(t.get("acceptance") or p.get("acceptance")),
            "expected": t.get("expect") or p.get("expect") or "the test passes",
            "actual": actual[:300],
            "status": r["status"],
        }
        if r["status"] == "failed":
            row["error"] = r["message"][:1500]
            row["fix"] = ""
        tests.append(row)
    for tid in tags.get("expected_tests", []):
        if tid not in seen:
            t = by_test.get(tid, {})
            tests.append({"name": tid, "level": t.get("level", "feature"), "features": split_list(t.get("features")),
                          "acceptance": split_list(t.get("acceptance")),
                          "expected": t.get("expect") or "the test runs and passes",
                          "actual": "did not run in this execution", "status": "not-executed"})
    tests.sort(key=lambda t: t["name"])
    count = lambda s: sum(t["status"] == s for t in tests)  # noqa: E731
    report = {
        "app": app_name,
        "command": record["command"],
        "framework": record["framework"],
        "date": record["finished_at"][:10],
        "execution": {k: record[k] for k in ("run_id", "runner", "cwd", "started_at", "finished_at", "exit_code",
                                              "log", "log_sha256", "results", "results_sha256", "approval")},
        "summary": {"total": len(tests), "passed": count("passed"), "failed": count("failed"),
                    "skipped": count("skipped"), "not_executed": count("not-executed"), "unverified": 0},
        "tests": tests,
    }
    return report


def to_markdown(report, not_testable=()):
    s, e = report["summary"], report["execution"]
    feats = {}
    for t in report["tests"]:
        for f in t["features"]:
            entry = feats.setdefault(f, {"passed": 0, "total": 0})
            entry["total"] += 1
            entry["passed"] += t["status"] == "passed"
    L = [f"# {report['app']}: integration report", "",
         f"Run `{e['run_id']}` by {e['runner']} · Command: `{report['command']}` · Framework: {report['framework']}",
         f"Started {e['started_at']} · Finished {e['finished_at']} · Exit code {e['exit_code']}",
         f"Evidence: `{e['log']}` (sha256 {e['log_sha256'][:12]}...), `{e['results']}` "
         f"(sha256 {e['results_sha256'][:12]}...)", "",
         "Statuses come from the results file of this run. Run `verify_tests.py` to check this report against "
         "the evidence; only verified passes prove a feature.", "",
         "## Summary", "",
         "| Total | Passed | Failed | Skipped | Not executed | Unverified |", "| --- | --- | --- | --- | --- | --- |",
         f"| {s['total']} | {s['passed']} | {s['failed']} | {s['skipped']} | {s['not_executed']} | {s['unverified']} |",
         "", "| Feature | Tests passed | Status |", "| --- | --- | --- |"]
    for f in sorted(feats):
        v = feats[f]
        L.append(f"| {f} | {v['passed']} of {v['total']} | {'passing' if v['passed'] == v['total'] else 'NOT passing'} |")
    L += ["", "## Results", "", "| Test | Level | Features | Acceptance | Expected | Actual | Status |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for t in report["tests"]:
        L.append(f"| {t['name']} | {t['level']} | {', '.join(t['features'])} | {', '.join(t['acceptance'])} | "
                 f"{t['expected']} | {t['actual'].replace('|', '/')} | {t['status']} |")
    L += ["", "## Failures and fixes", ""]
    fails = [t for t in report["tests"] if t["status"] in ("failed", "not-executed")]
    if fails:
        L += ["| Test | Status | Error | Features | Recommended fix |", "| --- | --- | --- | --- | --- |"]
        L += [f"| {t['name']} | {t['status']} | {t['actual'].replace('|', '/')} | {', '.join(t['features'])} | "
              f"{t.get('fix') or 'to do'} |" for t in fails]
    else:
        L.append("None in this run.")
    L += ["", "## Not testable here", ""]
    if not_testable:
        L += ["| What | Why | How the user can check it |", "| --- | --- | --- |"]
        L += [f"| {a} | {b} | {c} |" for a, b, c in not_testable]
    else:
        L.append("Nothing recorded.")
    return "\n".join(L) + "\n"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    parser = argparse.ArgumentParser(description="Run tests and record execution evidence.")
    parser.add_argument("--mixer", required=True)
    parser.add_argument("--cwd", required=True, help="folder to run the tests in")
    parser.add_argument("--unittest", metavar="START_DIR", help="use the built-in unittest harness")
    parser.add_argument("--top", default=".", help="top-level folder for unittest discovery")
    parser.add_argument("--junit", help="JUnit XML file the command writes (relative to --cwd)")
    parser.add_argument("--framework", default="other")
    parser.add_argument("--tags", help="JSON file mapping tests to features")
    parser.add_argument("--app", help="app name for the report (default: project.json name)")
    parser.add_argument("--approval", help="approval id in project.json for running these tests")
    parser.add_argument("--not-testable", help="JSON list of [what, why, how to check] rows for the report")
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.mixer) or not os.path.isdir(args.cwd):
        print("error: --mixer and --cwd must be folders")
        return 2
    if not args.unittest and not (args.junit and command):
        print("error: use --unittest START_DIR, or --junit FILE with a command after --")
        return 2
    try:
        tags = {}
        if args.tags:
            with open(args.tags, encoding="utf-8") as f:
                tags = json.load(f)
        record = execute(args.mixer, args.cwd, command, args.framework, args.junit, args.unittest, args.top,
                         args.approval)
        if not args.no_report:
            name = args.app
            pj = os.path.join(args.mixer, "project.json")
            if not name and os.path.exists(pj):
                with open(pj, encoding="utf-8") as f:
                    name = json.load(f).get("name")
            report = build_report(args.mixer, record, name or "app", tags)
            rows = []
            if args.not_testable:
                with open(args.not_testable, encoding="utf-8") as f:
                    rows = json.load(f)
            with open(os.path.join(args.mixer, "integration-report.json"), "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
                f.write("\n")
            with open(os.path.join(args.mixer, "integration-report.md"), "w", encoding="utf-8") as f:
                f.write(to_markdown(report, rows))
            s = report["summary"]
            print(f"run {record['run_id']}: exit {record['exit_code']}; {s['passed']} passed, {s['failed']} failed, "
                  f"{s['skipped']} skipped, {s['not_executed']} not executed")
        else:
            print(f"run {record['run_id']}: exit {record['exit_code']}")
    except (ValueError, OSError, ET.ParseError) as e:
        print(f"error: {e}")
        return 2
    if record["exit_code"] != 0:
        return 1
    if not args.no_report and (report["summary"]["failed"] or report["summary"]["not_executed"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
