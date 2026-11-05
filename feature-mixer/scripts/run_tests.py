#!/usr/bin/env python3
"""Run the unified app's tests, under an approval, and record evidence that they ran.

Usage (Python unittest, built-in harness):
    python3 run_tests.py --mixer mixer/ --cwd app/ --unittest tests [--top .] --approval A04

Usage (any framework that writes JUnit XML: pytest, jest-junit, vitest, go-junit-report...):
    python3 run_tests.py --mixer mixer/ --cwd app/ --junit reports/junit.xml --framework pytest \
        --approval A04 [--tags tags.json] -- pytest --junitxml=reports/junit.xml

Nothing runs without an approval that covers exactly this run: action
run-tests, the same folder, the same harness start/top or the same argument
list and JUnit path, not expired, not revoked, not used up (approvals.py
creates and checks them). Every attempt, accepted or refused, is logged in
mixer/approval-log.jsonl.

Limits (all recorded):
  --timeout SECONDS     default 1800. On timeout the whole process group is
                        sent SIGTERM, then SIGKILL after --kill-grace seconds
                        (Windows: taskkill /T /F). Processes left behind by a
                        run that exited normally are terminated too.
  --max-log-mb MB       default 50. Beyond it the log keeps the first and the
                        last half and records how many bytes were left out.
  --max-results-mb MB   default 50. A larger results file is not read.
  --expect-tests N      fewer executed tests than N makes the run incomplete.

What it records, in mixer/test-runs/<run-id>/ (files made read-only):
  output.log    everything the command printed (stdout and stderr, capped)
  results.xml   the per-test results (JUnit XML) as written by this run
  run.json      command (secrets redacted) and its SHA-256, framework, folder,
                times, exit code, outcome (exited, timed_out, interrupted),
                results status, counts, verdict, fingerprints of the log, the
                results and the tested code before and after, the approval,
                and an HMAC signature when --evidence-key is given
and appends the run to mixer/test-runs/ledger.jsonl (hash-chained).

Verdicts: passed (exit 0, at least one test executed, none failed, results
consistent), failed, no-tests (nothing executed: zero discovered or all
skipped), incomplete (fewer than --expect-tests), inconsistent (exit code
and results disagree, or the file's totals disagree with its test cases, or
a test has an unknown result), invalid-results (missing, malformed, stale or
too large), timed-out, interrupted. Only "passed" exits 0.

Then it writes mixer/integration-report.json and .md for this run, whatever
its verdict, so an earlier green report can never outlive a later run. A
JUnit file that exists before the run is moved into the run folder as
previous-<name> first, so only a file written during this run is accepted.

Test tags (which features a test proves) come from test docstrings in the
unittest harness ("features: M01, M04", "expect: ...", "level: ...",
"acceptance: AC01") or from a --tags JSON file:
    {"tests": {"<test id or name>": {"features": ["M01"], "expect": "...", "level": "api",
                                     "acceptance": ["AC01"]}},
     "expected_tests": ["<test id>", ...]}

Exit codes: 0 verdict passed; 1 any other verdict; 2 bad input (nothing ran);
3 refused: no valid approval (nothing ran); 130 interrupted.
"""

import argparse
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import approvals
import evidence

DEFAULT_TIMEOUT = 1800
DEFAULT_MAX_LOG_MB = 50
DEFAULT_MAX_RESULTS_MB = 50
KEY_ENV = "FEATURE_MIXER_EVIDENCE_KEY"

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
fails = sum(1 for r in res.rows if r[1] == "failed")
skips = sum(1 for r in res.rows if r[1] == "skipped")
with open(out, "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<testsuite name="unittest" tests="%d" failures="%d" '
            'skipped="%d">\n' % (len(res.rows), fails, skips))
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


class Refused(Exception):
    """No valid approval: nothing was executed."""


class RunInterrupted(Exception):
    pass


def sha256(path):
    return evidence.sha256_file(path)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def split_list(value):
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value or "").replace(";", ",").split(",") if v.strip()]


# --- results ----------------------------------------------------------------------------

KNOWN_CHILDREN = {"properties", "system-out", "system-err", "failure", "error", "skipped"}


def _int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_results(path, max_bytes=None):
    """Read a JUnit XML file strictly.

    Returns (cases, status, problems, warnings). status is ok, missing, too-large, malformed or
    inconsistent. Each case: {id, name, status, message, time, properties}. A case with an
    element this parser does not understand (flakyFailure, rerunFailure, ...) is 'unverified'."""
    if not os.path.isfile(path):
        return [], "missing", ["no results file"], []
    size = os.path.getsize(path)
    if max_bytes is not None and size > max_bytes:
        return [], "too-large", [f"results file is {size} bytes, above the {max_bytes}-byte limit"], []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        return [], "malformed", [f"results file is not valid XML ({e})"], []
    if root.tag not in ("testsuite", "testsuites"):
        return [], "malformed", [f"results file root is <{root.tag}>, not <testsuite> or <testsuites>"], []
    cases, problems, warnings = [], [], []
    for case in root.iter("testcase"):
        cls, name = case.get("classname", ""), case.get("name", "")
        if not name:
            problems.append("a <testcase> has no name")
            continue
        tid = f"{cls}.{name}" if cls else name
        status, message, kinds = "passed", "", []
        for child in case:
            kinds.append(child.tag)
            if child.tag in ("failure", "error"):
                status, message = "failed", child.get("message") or (child.text or "").strip()[:300]
            elif child.tag == "skipped" and status != "failed":
                status, message = "skipped", child.get("message") or "skipped"
            elif child.tag not in KNOWN_CHILDREN and status == "passed":
                status, message = "unverified", f"unrecognised result element <{child.tag}>"
        props = {p.get("name"): p.get("value", "") for p in case.iter("property")}
        cases.append({"id": tid, "name": name, "status": status, "message": message,
                      "time": case.get("time"), "properties": props})
    ids = [c["id"] for c in cases]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        warnings.append(f"{len(dupes)} test id(s) appear more than once: {', '.join(dupes[:5])}")
    # suite totals must agree with the test cases they contain
    for suite in root.iter("testsuite"):
        if suite.find("testsuite") is not None:
            continue
        own = [c for c in suite.findall("testcase")]
        sname = suite.get("name") or "(unnamed suite)"
        counts = {"tests": len(own),
                  "failures": sum(1 for c in own if c.find("failure") is not None),
                  "errors": sum(1 for c in own if c.find("error") is not None and c.find("failure") is None),
                  "skipped": sum(1 for c in own if c.find("skipped") is not None and c.find("failure") is None
                                 and c.find("error") is None)}
        for attr, have in counts.items():
            claimed = _int(suite.get(attr))
            if claimed is None:
                continue
            if attr == "failures" and suite.get("errors") is None:
                have = counts["failures"] + counts["errors"]
            if claimed != have:
                problems.append(f"suite {sname} says {attr}={claimed} but lists {have}")
    if root.tag == "testsuites":
        claimed = _int(root.get("tests"))
        if claimed is not None and claimed != len(cases):
            problems.append(f"<testsuites> says tests={claimed} but lists {len(cases)}")
    status = "inconsistent" if problems else "ok"
    return cases, status, problems, warnings


def parse_junit(path):
    """[{id, name, status, message, time, properties}]. Raises ValueError on a missing or malformed file."""
    cases, status, problems, _ = parse_results(path)
    if status in ("missing", "malformed", "too-large"):
        raise ValueError("; ".join(problems))
    return cases


def counts_of(cases):
    c = {"total": len(cases)}
    for s in ("passed", "failed", "skipped", "unverified"):
        c[s] = sum(1 for x in cases if x["status"] == s)
    c["executed"] = c["total"] - c["skipped"]
    return c


def decide_verdict(outcome, exit_code, results_status, counts, expect_tests=None):
    """Return (verdict, problems). Only 'passed' means the run proves anything passed as a whole."""
    problems = []
    if outcome == "timed_out":
        return "timed-out", ["the run was stopped at its timeout"]
    if outcome == "interrupted":
        return "interrupted", ["the run was interrupted"]
    if results_status in ("missing", "malformed", "too-large", "stale"):
        return "invalid-results", [f"results {results_status}"]
    if results_status == "inconsistent":
        problems.append("the results file contradicts itself")
    if counts["executed"] == 0:
        return "no-tests", problems + ["no test executed (none discovered, or every test skipped)"]
    if counts["failed"]:
        if exit_code == 0:
            problems.append(f"exit code 0 although {counts['failed']} test(s) failed")
        return "failed", problems
    if exit_code != 0:
        problems.append(f"exit code {exit_code} although no test failed")
    if counts["unverified"]:
        problems.append(f"{counts['unverified']} test(s) have a result this runner does not recognise")
    if problems:
        return "inconsistent", problems
    if expect_tests is not None and counts["executed"] < expect_tests:
        return "incomplete", [f"{counts['executed']} test(s) executed, fewer than the {expect_tests} expected"]
    return "passed", []


# --- running ------------------------------------------------------------------------------

class LogSink:
    """Write output to a file, keeping the first and last halves when it is too long."""

    def __init__(self, path, max_bytes):
        self.f = open(path, "wb")
        self.head_limit = max_bytes // 2
        self.tail_limit = max_bytes - self.head_limit
        self.tail = bytearray()
        self.total = 0
        self.head = 0
        self.lock = threading.Lock()
        self.closed = False

    def write(self, chunk):
        with self.lock:
            if self.closed:
                return
            self.total += len(chunk)
            if self.head < self.head_limit:
                take = min(len(chunk), self.head_limit - self.head)
                self.f.write(chunk[:take])
                self.f.flush()
                self.head += take
                chunk = chunk[take:]
            if chunk:
                self.tail += chunk
                if len(self.tail) > self.tail_limit:
                    del self.tail[:len(self.tail) - self.tail_limit]

    def close(self):
        with self.lock:
            if self.closed:
                return
            omitted = self.total - self.head - len(self.tail)
            if omitted > 0:
                self.f.write(f"\n[... {omitted} bytes of output omitted by run_tests.py ...]\n".encode())
            self.f.write(bytes(self.tail))
            self.f.close()
            self.closed = True
            self.omitted = max(omitted, 0)


def _reader(fd, sink):
    while True:
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        sink.write(chunk)


def _group_alive(pgid):
    try:
        os.killpg(pgid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _terminate(proc, grace):
    """Terminate the command and everything it started. Returns a description of what was done."""
    info = {"signals": []}
    if os.name == "nt":
        info["method"] = "taskkill /T /F"
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        info["signals"].append("taskkill")
        try:
            proc.wait(grace)
        except subprocess.TimeoutExpired:
            proc.kill()
            info["signals"].append("kill")
        return info
    info["method"] = "process group"
    pgid = proc.pid  # start_new_session made the command the leader of its own group
    try:
        os.killpg(pgid, signal.SIGTERM)
        info["signals"].append("SIGTERM")
    except ProcessLookupError:
        return info
    deadline = time.time() + grace
    while time.time() < deadline:
        proc.poll()
        if proc.returncode is not None and not _group_alive(pgid):
            break
        time.sleep(0.05)
    if proc.poll() is None or _group_alive(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
            info["signals"].append("SIGKILL")
        except ProcessLookupError:
            pass
    proc.wait()
    return info


def spawn(argv, cwd, log_path, timeout, grace, max_log_bytes):
    """Run argv with a timeout and output capture. Returns a dict describing what happened."""
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else \
        {"start_new_session": True}
    sink = LogSink(log_path, max_log_bytes)
    try:
        proc = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, **kwargs)
    except OSError:
        sink.close()
        raise
    reader = threading.Thread(target=_reader, args=(proc.stdout.fileno(), sink), daemon=True)
    reader.start()
    result = {"outcome": "exited", "timeout_seconds": timeout, "termination": None}
    started = time.time()
    previous = None
    if os.name != "nt" and threading.current_thread() is threading.main_thread():
        def _on_term(signum, frame):
            raise RunInterrupted()
        previous = signal.signal(signal.SIGTERM, _on_term)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        result["outcome"] = "timed_out"
        result["termination"] = dict(_terminate(proc, grace), reason=f"timeout after {timeout} s")
    except (KeyboardInterrupt, RunInterrupted):
        result["outcome"] = "interrupted"
        result["termination"] = dict(_terminate(proc, grace), reason="run_tests.py was interrupted")
    finally:
        if previous is not None:
            signal.signal(signal.SIGTERM, previous)
    if result["outcome"] == "exited" and os.name != "nt" and _group_alive(proc.pid):
        result["termination"] = dict(_terminate(proc, grace),
                                     reason="processes the tests started were still running after they finished")
    result["duration_seconds"] = round(time.time() - started, 3)
    reader.join(timeout=5)
    if reader.is_alive():
        result["output_still_open"] = ("a process outside the command's process group kept the output open; "
                                       "it may still be running")
    try:
        proc.stdout.close()
    except OSError:
        pass
    sink.close()
    result["exit_code"] = proc.returncode
    result["log_bytes_total"] = sink.total
    result["log_bytes_omitted"] = getattr(sink, "omitted", 0)
    return result


def _new_run_dir(mixer_dir):
    for _ in range(5):
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + secrets.token_hex(3)
        run_dir = os.path.join(mixer_dir, "test-runs", run_id)
        try:
            os.makedirs(run_dir)
            return run_id, run_dir
        except FileExistsError:
            continue
    raise ValueError("could not create a unique run folder")


def execute(mixer_dir, cwd, argv, framework, junit=None, unittest_start=None, top=".", approval=None,
            display_command=None, timeout=DEFAULT_TIMEOUT, kill_grace=5, max_log_bytes=None,
            max_results_bytes=None, expect_tests=None, key_file=None, evidence_copy=None,
            authorised_by="run_tests.py"):
    """Authorise, run the command, store the evidence and return the run record.
    Raises Refused (nothing ran) or ValueError (bad input, nothing ran)."""
    if timeout is None or timeout <= 0:
        raise ValueError("--timeout must be a positive number of seconds")
    max_log_bytes = max_log_bytes or DEFAULT_MAX_LOG_MB * 1024 * 1024
    max_results_bytes = max_results_bytes or DEFAULT_MAX_RESULTS_MB * 1024 * 1024
    key, key_id, key_warning = evidence.load_key(key_file or os.environ.get(KEY_ENV), mixer_dir)
    user_argv = list(argv or [])
    scope = approvals.make_scope(mixer_dir, cwd, unittest_start, top, user_argv, junit)
    try:
        approvals.authorise(mixer_dir, approval, "run-tests", scope, cwd=cwd, by=authorised_by)
    except approvals.Refused as e:
        raise Refused(str(e))

    with evidence.RunLock(mixer_dir) as lock:
        run_id, run_dir = _new_run_dir(mixer_dir)
        log_path = os.path.join(run_dir, "output.log")
        results_path = os.path.join(run_dir, "results.xml")
        moved = None
        if unittest_start:
            exec_argv = [sys.executable, "-c", HARNESS, unittest_start, top, os.path.abspath(results_path)]
            display_command = display_command or f"python -m unittest discover -s {unittest_start} -t {top} " \
                                                  "(Feature Mixer harness)"
            framework = "unittest"
        else:
            exec_argv = user_argv
            src = junit if os.path.isabs(junit) else os.path.join(cwd, junit)
            if os.path.lexists(src):  # only a file written by this run counts
                moved = os.path.join(run_dir, "previous-" + os.path.basename(src))
                shutil.move(src, moved)
        code_before, files_before = approvals.code_fingerprint(mixer_dir, cwd, junit)
        started_at = now()
        try:
            proc = spawn(exec_argv, cwd, log_path, timeout, kill_grace, max_log_bytes)
        except OSError as e:
            raise ValueError(f"could not run {exec_argv[0]}: {e.strerror}")
        finished_at = now()
        code_after, _ = approvals.code_fingerprint(mixer_dir, cwd, junit)

        results_status, problems, warnings = "missing", [], []
        if not unittest_start:
            if os.path.isfile(src):
                if os.path.getsize(src) > max_results_bytes:
                    results_status = "too-large"
                    problems = [f"{junit} is {os.path.getsize(src)} bytes, above the limit; not copied"]
                else:
                    shutil.copyfile(src, results_path)
            elif proc["outcome"] == "exited":
                problems = [f"the command did not write {junit} during this run"
                            + (" (an older copy was moved aside first)" if moved else "")]
        cases = []
        if os.path.isfile(results_path):
            cases, results_status, problems, warnings = parse_results(results_path, max_results_bytes)
        counts = counts_of(cases)
        verdict, why = decide_verdict(proc["outcome"], proc["exit_code"], results_status, counts, expect_tests)
        if not os.path.isfile(results_path):
            with open(results_path, "w", encoding="utf-8") as f:  # an empty, valid placeholder: nothing ran
                f.write('<?xml version="1.0" encoding="utf-8"?>\n<testsuite name="none" tests="0"/>\n')
        record = {
            "format": 2,
            "run_id": run_id,
            "runner": "run_tests.py",
            "authorised_by": authorised_by,
            "command": display_command or " ".join(approvals.redact_argv(user_argv)),
            "argv": ["<harness>", unittest_start, top] if unittest_start else approvals.redact_argv(user_argv),
            "argv_sha256": approvals.argv_sha256(user_argv) if not unittest_start else None,
            "framework": framework,
            "cwd": approvals.rel_cwd(mixer_dir, cwd),
            "started_at": started_at,
            "finished_at": finished_at,
            "exit_code": proc["exit_code"],
            "outcome": proc["outcome"],
            "duration_seconds": proc["duration_seconds"],
            "timeout_seconds": timeout,
            "termination": proc["termination"],
            "results_status": results_status,
            "results_problems": problems,
            "results_warnings": warnings,
            "counts": counts,
            "verdict": verdict,
            "verdict_reasons": why,
            "expect_tests": expect_tests,
            "log": os.path.relpath(log_path, mixer_dir).replace("\\", "/"),
            "log_sha256": sha256(log_path),
            "log_bytes_total": proc["log_bytes_total"],
            "log_bytes_omitted": proc["log_bytes_omitted"],
            "results": os.path.relpath(results_path, mixer_dir).replace("\\", "/"),
            "results_sha256": sha256(results_path),
            "previous_results_moved_to": os.path.relpath(moved, mixer_dir).replace("\\", "/") if moved else None,
            "code_sha256_before": code_before,
            "code_sha256_after": code_after,
            "code_files": files_before,
            "approval": approval,
            "unittest": {"start": unittest_start, "top": top} if unittest_start else None,
            "junit": junit,
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "lock_taken_over": lock.took_over,
        }
        if proc.get("output_still_open"):
            record["output_still_open"] = proc["output_still_open"]
        if key:
            record["evidence_key_id"] = key_id
            if key_warning:
                record["evidence_key_warning"] = key_warning
            record["hmac"] = evidence.sign(key, record)
        run_json = os.path.join(run_dir, "run.json")
        with open(run_json, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
            f.write("\n")
        record["run_record_sha256"] = sha256(run_json)
        for name in os.listdir(run_dir):
            evidence.make_read_only(os.path.join(run_dir, name))
        evidence.append_ledger(mixer_dir, run_id, record["run_record_sha256"], key)
        if evidence_copy:
            record["evidence_copy"] = evidence.copy_run(run_dir, evidence_copy)
    return record


# --- report ------------------------------------------------------------------------------------

EXECUTION_KEYS = ("run_id", "runner", "cwd", "started_at", "finished_at", "exit_code", "log", "log_sha256", "results",
                  "results_sha256", "approval", "outcome", "verdict", "results_status", "run_record_sha256",
                  "code_sha256_after", "timeout_seconds", "duration_seconds")


def build_report(mixer_dir, record, app_name, tags=None):
    tags = tags or {}
    by_test = tags.get("tests", {})
    try:
        results, _, _, _ = parse_results(os.path.join(mixer_dir, record["results"]))
    except OSError:
        results = []
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
    why = {"timed-out": f"the run timed out after {record.get('timeout_seconds')} s",
           "interrupted": "the run was interrupted", "invalid-results": "the run produced no usable results"}
    for tid in tags.get("expected_tests", []):
        if tid not in seen:
            t = by_test.get(tid, {})
            tests.append({"name": tid, "level": t.get("level", "feature"), "features": split_list(t.get("features")),
                          "acceptance": split_list(t.get("acceptance")),
                          "expected": t.get("expect") or "the test runs and passes",
                          "actual": why.get(record.get("verdict"), "did not run in this execution"),
                          "status": "not-executed"})
    tests.sort(key=lambda t: t["name"])
    count = lambda s: sum(t["status"] == s for t in tests)  # noqa: E731
    report = {
        "app": app_name,
        "command": record["command"],
        "framework": record["framework"],
        "date": record["finished_at"][:10],
        "execution": {k: record.get(k) for k in EXECUTION_KEYS},
        "summary": {"total": len(tests), "passed": count("passed"), "failed": count("failed"),
                    "skipped": count("skipped"), "not_executed": count("not-executed"),
                    "unverified": count("unverified"), "verdict": record.get("verdict", "passed")},
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
         f"Started {e['started_at']} · Finished {e['finished_at']} · Exit code {e['exit_code']} · "
         f"Outcome {e.get('outcome') or 'exited'} · **Verdict: {s.get('verdict', 'passed')}**",
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
    if not report["tests"]:
        L.append("| (none) | | | | | no test ran | |")
    L += ["", "## Failures and fixes", ""]
    fails = [t for t in report["tests"] if t["status"] in ("failed", "not-executed", "unverified")]
    if fails:
        L += ["| Test | Status | Error | Features | Recommended fix |", "| --- | --- | --- | --- | --- |"]
        L += [f"| {t['name']} | {t['status']} | {t['actual'].replace('|', '/')} | {', '.join(t['features'])} | "
              f"{t.get('fix') or 'to do'} |" for t in fails]
    elif s.get("verdict", "passed") != "passed":
        L.append(f"The run's verdict is {s.get('verdict')}: it proves nothing passed.")
    else:
        L.append("None in this run.")
    L += ["", "## Not testable here", ""]
    if not_testable:
        L += ["| What | Why | How the user can check it |", "| --- | --- | --- |"]
        L += [f"| {a} | {b} | {c} |" for a, b, c in not_testable]
    else:
        L.append("Nothing recorded.")
    return "\n".join(L) + "\n"


def write_report(mixer_dir, report, rows=()):
    evidence.atomic_write_json(os.path.join(mixer_dir, "integration-report.json"), report)
    evidence.atomic_write_text(os.path.join(mixer_dir, "integration-report.md"), to_markdown(report, rows))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    parser = argparse.ArgumentParser(description="Run tests under an approval and record execution evidence.")
    parser.add_argument("--mixer", required=True)
    parser.add_argument("--cwd", required=True, help="folder to run the tests in")
    parser.add_argument("--unittest", metavar="START_DIR", help="use the built-in unittest harness")
    parser.add_argument("--top", default=".", help="top-level folder for unittest discovery")
    parser.add_argument("--junit", help="JUnit XML file the command writes (relative to --cwd)")
    parser.add_argument("--framework", default="other")
    parser.add_argument("--tags", help="JSON file mapping tests to features")
    parser.add_argument("--app", help="app name for the report (default: project.json name)")
    parser.add_argument("--approval", help="the approval id that covers exactly this run (required)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds (default 1800)")
    parser.add_argument("--kill-grace", type=float, default=5, help="seconds between SIGTERM and SIGKILL")
    parser.add_argument("--max-log-mb", type=float, default=DEFAULT_MAX_LOG_MB)
    parser.add_argument("--max-results-mb", type=float, default=DEFAULT_MAX_RESULTS_MB)
    parser.add_argument("--expect-tests", type=int, help="the minimum number of tests that must execute")
    parser.add_argument("--evidence-key", help=f"HMAC key file kept outside mixer/ (or set {KEY_ENV})")
    parser.add_argument("--evidence-copy", help="also copy the run's evidence to this folder")
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
        rows = []
        if args.not_testable:
            with open(args.not_testable, encoding="utf-8") as f:
                rows = json.load(f)
        record = execute(args.mixer, args.cwd, command, args.framework, args.junit, args.unittest, args.top,
                         args.approval, timeout=args.timeout, kill_grace=args.kill_grace,
                         max_log_bytes=int(args.max_log_mb * 1024 * 1024),
                         max_results_bytes=int(args.max_results_mb * 1024 * 1024), expect_tests=args.expect_tests,
                         key_file=args.evidence_key, evidence_copy=args.evidence_copy)
    except Refused as e:
        print(f"refused: {e}. Nothing was run. Ask the user, then record the approval with approvals.py grant.")
        return 3
    except (ValueError, OSError) as e:
        print(f"error: {e}")
        return 2
    if not args.no_report:
        name = args.app
        pj = os.path.join(args.mixer, "project.json")
        if not name and os.path.exists(pj):
            with open(pj, encoding="utf-8") as f:
                name = json.load(f).get("name")
        report = build_report(args.mixer, record, name or "app", tags)
        write_report(args.mixer, report, rows)
        s = report["summary"]
        print(f"run {record['run_id']}: {record['outcome']}, exit {record['exit_code']}, verdict {record['verdict']}; "
              f"{s['passed']} passed, {s['failed']} failed, {s['skipped']} skipped, {s['not_executed']} not executed")
    else:
        print(f"run {record['run_id']}: {record['outcome']}, exit {record['exit_code']}, verdict {record['verdict']}")
    for reason in record["verdict_reasons"] + [p for p in record["results_problems"]
                                               if p not in record["verdict_reasons"]]:
        print(f"  - {reason}")
    if record["outcome"] == "interrupted":
        return 130
    if record["verdict"] != "passed":
        return 1
    if not args.no_report and (report["summary"]["failed"] or report["summary"]["not_executed"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
