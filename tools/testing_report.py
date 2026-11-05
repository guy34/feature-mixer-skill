#!/usr/bin/env python3
"""Run the release verification checklist and write docs/TESTING-REPORT.md.

    python3 tools/testing_report.py [--previous DIR] [--benchmarks DIR] [--pythons auto]

Every row in the report is a command this script actually ran, with its exit code, duration and the last
lines of its output. Nothing is typed in by hand. Runs that would change the repository (the example's test
run, packaging) happen in temporary copies.

--previous DIR    the previous release's repository (for example a 2.1.0 checkout): its tests are run against
                  this release's code, its probes are compared with this release's, and its validators are
                  compared with this release's on the old workspaces
--benchmarks DIR  a folder of benchmark runs (as aggregate.py expects) to score
--pythons auto    also run the suite under every Python found by `uv python find` (3.8 to 3.13)
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "feature-mixer", "scripts")
EX = os.path.join(ROOT, "examples", "team-hub")
PY = sys.executable
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
rows, extra = [], {}

COUNTER = r'''
import json, sys, time, unittest
sys.path.insert(0, sys.argv[1])
loader = unittest.defaultTestLoader
suite = loader.discover(sys.argv[1], top_level_dir=sys.argv[1])
per, t0 = {}, time.time()
class R(unittest.TextTestResult):
    def _add(self, t, k):
        mod = t.id().split(".")[0]
        if mod == "unittest":   # a module that failed to import
            mod = "import errors"
        per.setdefault(mod, {"passed": 0, "failed": 0, "skipped": 0})[k] += 1
    def addSuccess(self, t): super().addSuccess(t); self._add(t, "passed")
    def addFailure(self, t, e): super().addFailure(t, e); self._add(t, "failed")
    def addError(self, t, e): super().addError(t, e); self._add(t, "failed")
    def addSkip(self, t, r): super().addSkip(t, r); self._add(t, "skipped")
    def addExpectedFailure(self, t, e): super().addExpectedFailure(t, e); self._add(t, "passed")
    def addUnexpectedSuccess(self, t): super().addUnexpectedSuccess(t); self._add(t, "failed")
discovered = suite.countTestCases()
res = unittest.TextTestRunner(resultclass=R, stream=open("/dev/null", "w")).run(suite)
print(json.dumps({"discovered": discovered, "modules": per, "seconds": round(time.time() - t0, 1)}))
'''


def run(step, label, cmd, cwd=ROOT, expect=0, tail=6, timeout=1800):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=ENV, timeout=timeout)
        code, out = r.returncode, (r.stdout + r.stderr).strip().splitlines()
    except subprocess.TimeoutExpired:
        code, out = "timed out", [f"stopped after {timeout} s"]
    shown = [line for line in out if line.strip()][-tail:]
    ok = code == expect
    rows.append({"step": step, "label": label, "cmd": " ".join(_short(c) for c in cmd), "exit": code,
                 "expect": expect, "ok": ok or expect is None, "secs": round(time.time() - t0, 1), "out": shown})
    print(f"{'ran' if expect is None else 'ok ' if ok else 'BAD'} [{code}] {label}")
    return code, out


def _short(c):
    c = str(c)
    for base, name in ((ROOT, "."), (tempfile.gettempdir(), "$TMP"), (os.path.expanduser("~"), "~")):
        c = c.replace(base, name)
    return c if " " not in c else f'"{c}"'


def counts(python=PY, tests_dir=None):
    tests_dir = tests_dir or os.path.join(ROOT, "tests")
    t0 = time.time()
    try:
        r = subprocess.run([python, "-c", COUNTER, tests_dir], cwd=os.path.dirname(tests_dir), capture_output=True,
                           text=True, env=ENV, timeout=1800)
        data = json.loads(r.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        return {"timed_out": True, "seconds": round(time.time() - t0, 1)}
    except (ValueError, IndexError):
        return {"error": (r.stderr or r.stdout)[-500:]}
    tot = {k: sum(m[k] for m in data["modules"].values()) for k in ("passed", "failed", "skipped")}
    executed = tot["passed"] + tot["failed"] + tot["skipped"]
    data.update(tot, total=executed, not_executed=max(data["discovered"] - executed, 0), timed_out=0)
    return data


def pythons():
    found = []
    for v in ("3.8", "3.9", "3.10", "3.11", "3.12", "3.13"):
        try:
            p = subprocess.run(["uv", "python", "find", v], capture_output=True, text=True).stdout.strip()
        except OSError:
            p = shutil.which(f"python{v}") or ""
        if p and os.path.exists(p):
            found.append((v, p))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write docs/TESTING-REPORT.md from real runs.")
    ap.add_argument("--previous")
    ap.add_argument("--benchmarks")
    ap.add_argument("--pythons", default="")
    a = ap.parse_args(argv)
    tests = lambda *names: [PY, "-m", "unittest", *names]  # noqa: E731
    tdir = os.path.join(ROOT, "tests")

    # 1-2: suites
    extra["totals"] = counts()
    run(1, "Existing tests (2.0 and 2.1 test files, as updated)",
        tests("test_feature_menu", "test_dependencies", "test_compatibility", "test_artifacts", "test_security",
              "test_test_verification", "test_intelligence", "test_release", "test_benchmarks",
              "test_benchmark_findings"), tdir)
    run(2, "New 2.2 adversarial and failure tests",
        tests("test_execution_safety", "test_adversarial_sources", "test_compatibility_failures",
              "test_integration_scenarios", "test_robustness", "test_workflow_guards"), tdir)
    run(2, "Whole suite", tests("discover", "-s", "tests"))
    # 3: benchmarks (deterministic parts)
    code, out = run(3, "Weakness probes against this release (all must be defended)",
                    [PY, "benchmarks/probes/run_probes.py", "feature-mixer"], tail=3, timeout=900)
    probes_now = subprocess.run([PY, "benchmarks/probes/run_probes.py", "feature-mixer", "--json"], cwd=ROOT,
                                capture_output=True, text=True, env=ENV, timeout=900)
    extra["probes_now"] = json.loads(probes_now.stdout)["results"]
    if a.previous:
        old = subprocess.run([PY, "benchmarks/probes/run_probes.py", os.path.join(a.previous, "feature-mixer"),
                              "--json"], cwd=ROOT, capture_output=True, text=True, env=ENV, timeout=900)
        extra["probes_previous"] = json.loads(old.stdout)["results"]
    for name in ("J-auth", "K-tenancy", "L-rules", "M-payments", "N-files", "O-api"):
        for impl, want in (("reference", 0), ("naive", 1)):
            run(3, f"Integration scenario {name}: hidden tests on the {impl} build",
                [PY, "benchmarks/integration/run_holdout.py", f"benchmarks/integration/{name}",
                 f"benchmarks/integration/{name}/{impl}"], expect=want, tail=1)
    # 4: clean install
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "repo")
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "dist"))
        run(4, "Package both zips (in a copy)", [PY, "tools/release_check.py", "--clean", "--package",
                                                 os.path.join(tmp, "dist")], copy, tail=3)
        unz = os.path.join(tmp, "unzipped")
        if os.path.exists(os.path.join(tmp, "dist", "feature-mixer-skill.zip")):
            with zipfile.ZipFile(os.path.join(tmp, "dist", "feature-mixer-skill.zip")) as z:
                z.extractall(unz)
            with zipfile.ZipFile(os.path.join(tmp, "dist", "feature-mixer-claude-ai.zip")) as z:
                z.extractall(os.path.join(tmp, "skills"))
            run(4, "Clean install: the suite from the unzipped repository", tests("discover", "-s", "tests"),
                os.path.join(unz, "feature-mixer-skill"))
            run(4, "Clean install: the Claude.ai zip's scripts answer --help from an unrelated folder",
                [PY, os.path.join(tmp, "skills", "feature-mixer", "scripts", "run_tests.py"), "--help"], tmp, tail=2)
        # 9: example, in a copy
        run(9, "Example: run the app's tests via run_tests.py under approval A01 and verify (in a copy)",
            [PY, "run_integration.py"], os.path.join(copy, "examples", "team-hub", "app"))
        run(9, "Example: full project validation after the fresh run (copy)",
            [PY, os.path.join(copy, "feature-mixer", "scripts", "validate_project.py"),
             os.path.join(copy, "examples", "team-hub", "mixer")])
    run(9, "Example: verify the committed test evidence", [PY, f"{S}/verify_tests.py", f"{EX}/mixer", "--no-write"])
    # 5-7: platforms, Pythons, static checks
    extra["platform"] = f"{platform.system()} {platform.release()} ({platform.machine()})"
    if a.pythons == "auto":
        extra["pythons"] = {}
        for v, p in pythons():
            extra["pythons"][v] = counts(p)
            print(f"python {v}: {extra['pythons'][v].get('passed')} passed, {extra['pythons'][v].get('failed')} failed")
    if shutil.which("flake8"):
        run(7, "Static check: pyflakes-class errors (undefined names, unused imports, syntax)",
            ["flake8", "--select", "F,E9", "feature-mixer/scripts", "tools", "tests", "benchmarks/score.py",
             "benchmarks/aggregate.py", "benchmarks/prepare_run.py", "benchmarks/probes",
             "benchmarks/integration/run_holdout.py", "examples/team-hub/app"], tail=10)
    if shutil.which("vermin"):
        run(6, "Python compatibility: minimum version of the shipped code (vermin)",
            ["vermin", "--no-tips", "-t=3.8-", "--violations", "feature-mixer/scripts", "tools", "tests",
             "benchmarks/score.py", "benchmarks/aggregate.py", "benchmarks/probes", "examples/team-hub/app"], tail=3)
    # 8: schemas
    run(8, "Schemas, templates, discovery, references, scripts, install docs, plugin CLI, secrets",
        [PY, "tools/release_check.py", "--clean"], tail=14)
    run(8, "Every artifact in the example against its schema", [PY, f"{S}/validate_artifacts.py", f"{EX}/mixer"])
    # 10: previous workflows
    run(10, "Regression: the frozen 2.0 workspace validates", [PY, f"{S}/validate_project.py",
                                                               "tests/fixtures/v2_0_workspace/mixer"], tail=3)
    olds = sorted(os.path.join("benchmarks", "runs", n, "mixer") for n in os.listdir(os.path.join(ROOT, "benchmarks",
                                                                                                 "runs"))
                  if os.path.isdir(os.path.join(ROOT, "benchmarks", "runs", n, "mixer")))
    verdicts = []
    for m in olds:
        new = subprocess.run([PY, f"{S}/validate_project.py", m], cwd=ROOT, capture_output=True, env=ENV).returncode
        old = subprocess.run([PY, os.path.join(a.previous, "feature-mixer", "scripts", "validate_project.py"), m],
                             cwd=ROOT, capture_output=True, env=ENV).returncode if a.previous else "n/a"
        verdicts.append((m, old, new))
    extra["old_workspaces"] = verdicts
    if a.previous:
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, "repo")
            skip = shutil.ignore_patterns(".git", "__pycache__")
            shutil.copytree(ROOT, copy, ignore=lambda d, names: set(skip(d, names)) |
                            ({"tests"} if os.path.abspath(d) == ROOT else set()))
            shutil.copytree(os.path.join(a.previous, "tests"), os.path.join(copy, "tests"),
                            ignore=shutil.ignore_patterns("__pycache__"))
            extra["previous_tests"] = counts(PY, os.path.join(copy, "tests"))
            r = subprocess.run(tests("discover", "-s", "tests"), cwd=copy, capture_output=True, text=True, env=ENV)
            extra["previous_failures"] = [line for line in (r.stdout + r.stderr).splitlines()
                                          if line.startswith(("FAIL:", "ERROR:"))]
    if a.benchmarks:
        run(3, "Benchmark runs: score and aggregate", [PY, "benchmarks/aggregate.py", a.benchmarks, "--md"],
            expect=None, tail=60)
    write()
    bad = [r for r in rows if not r["ok"]]
    return 1 if bad else 0


def write():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    t = extra.get("totals", {})
    L = ["# Testing and validation report", "",
         f"Generated by `tools/testing_report.py` on {now}, Python {platform.python_version()} on "
         f"{extra.get('platform')}. Every row is a command that ran; outputs are the last lines it printed. "
         "Nothing here is typed in by hand.", "",
         "## Totals", "",
         "| Discovered | Ran | Passed | Failed | Skipped | Not executed | Timed out | Seconds |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |",
         f"| {t.get('discovered')} | {t.get('total')} | {t.get('passed')} | {t.get('failed')} | {t.get('skipped')} | "
         f"{t.get('not_executed')} | {1 if t.get('timed_out') else 0} | {t.get('seconds')} |", "",
         "| Test module | Passed | Failed | Skipped |", "| --- | --- | --- | --- |"]
    for mod, c in sorted((t.get("modules") or {}).items()):
        L.append(f"| {mod} | {c['passed']} | {c['failed']} | {c['skipped']} |")
    if extra.get("pythons"):
        L += ["", "## Python versions", "", "| Python | Passed | Failed | Skipped | Not executed | Seconds |",
              "| --- | --- | --- | --- | --- | --- |"]
        for v, c in extra["pythons"].items():
            L.append(f"| {v} | {c.get('passed')} | {c.get('failed')} | {c.get('skipped')} | {c.get('not_executed')} | "
                     f"{c.get('seconds')} |")
        L += ["", f"Platform: {extra.get('platform')}. **Windows and macOS were not run.** The code paths Windows "
              "uses (the portable walker, `taskkill`) are exercised on Linux only where they can be "
              "(`PortableWalkTest`); `taskkill` itself is not."]
    if extra.get("probes_now"):
        prev = {r["id"]: r for r in extra.get("probes_previous", [])}
        L += ["", "## Weakness probes", "", "The same attacks against the previous release and this one "
              "(`benchmarks/probes/run_probes.py`).", "",
              "| Probe | Area | What it tries | Previous | This release |", "| --- | --- | --- | --- | --- |"]
        for r in extra["probes_now"]:
            L.append(f"| {r['id']} | {r['area']} | {r['probe']} | {prev.get(r['id'], {}).get('status', 'n/a')} | "
                     f"{r['status']} |")
        cnt = lambda rs, s: sum(1 for r in rs if r["status"] == s)  # noqa: E731
        if prev:
            L.append(f"\nPrevious: {cnt(prev.values(), 'vulnerable')} vulnerable, {cnt(prev.values(), 'defended')} "
                     f"defended. This release: {cnt(extra['probes_now'], 'vulnerable')} vulnerable, "
                     f"{cnt(extra['probes_now'], 'defended')} defended, {cnt(extra['probes_now'], 'error')} error.")
    if extra.get("old_workspaces"):
        L += ["", "## Older workspaces", "", "Validator exit codes on the workspaces written by earlier releases "
              "(0 valid, 1 problems). The same verdict from both means nothing that worked stopped working.", "",
              "| Workspace | Previous release | This release |", "| --- | --- | --- |"]
        L += [f"| `{m}` | {o} | {n} |" for m, o, n in extra["old_workspaces"]]
    if extra.get("previous_tests"):
        pt = extra["previous_tests"]
        L += ["", "## The previous release's own tests against this code", "",
              f"{pt.get('passed')} passed, {pt.get('failed')} failed, {pt.get('skipped')} skipped. These are the "
              "previous release's test files, byte for byte. A failure is expected only where behaviour changed "
              "on purpose; each is listed here:", ""]
        L += [f"- `{x}`" for x in extra.get("previous_failures", [])] or ["- none"]
    L += ["", "## Checks", "", "| # | Check | Exit | Expected | Result | Seconds |", "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        exp = "any" if r["expect"] is None else r["expect"]
        res = "as expected" if r["ok"] else "UNEXPECTED"
        L.append(f"| {r['step']} | {r['label']} | {r['exit']} | {exp} | {res} | {r['secs']} |")
    L += ["", "Steps follow the release checklist: 1 existing tests, 2 new adversarial tests, 3 benchmark "
          "scenarios (probes, hidden tests, scores), 4 installation from a clean copy, 5 platforms, 6 Python "
          "compatibility, 7 static checks, 8 schemas, 9 the example, 10 previous workflows.", ""]
    for r in rows:
        L += [f"### {r['step']}. {r['label']}", "", f"`{r['cmd']}` → exit {r['exit']}", "", "```"]
        L += r["out"] or ["(no output)"]
        L += ["```", ""]
    with open(os.path.join(ROOT, "docs", "TESTING-REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
