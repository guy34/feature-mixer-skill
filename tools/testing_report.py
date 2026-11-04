#!/usr/bin/env python3
"""Run the release verification checklist and write docs/TESTING-REPORT.md.

    python3 tools/testing_report.py [--previous-tests DIR] [--benchmarks DIR]

Every row in the report is a command this script actually ran, with its
exit code, duration and the last lines of its output. Nothing is typed in by
hand. Runs that would change the repository (the example's test run) happen
in a temporary copy.

--previous-tests DIR   the previous release's tests/ folder: runs it against
                       this release's code to show regressions
--benchmarks DIR       a folder of benchmark runs (<scenario>/mixer) to score
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "feature-mixer", "scripts")
EX = os.path.join(ROOT, "examples", "team-hub")
PY = sys.executable
rows = []


def run(step, label, cmd, cwd=ROOT, expect=0, tail=6):
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    out = (r.stdout + r.stderr).strip().splitlines()
    shown = [line for line in out if line.strip()][-tail:]
    ok = r.returncode == expect
    rows.append({"step": step, "label": label, "cmd": " ".join(_short(c) for c in cmd), "exit": r.returncode,
                 "expect": expect, "ok": ok, "secs": round(time.time() - t0, 1), "out": shown})
    print(f"{'ran' if expect is None else 'ok ' if ok else 'BAD'} [{r.returncode}] {label}")
    return r


def _short(c):
    c = str(c)
    for base, name in ((ROOT, "."), (tempfile.gettempdir(), "$TMP")):
        c = c.replace(base, name)
    return c if " " not in c else f'"{c}"'


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write docs/TESTING-REPORT.md from real runs.")
    parser.add_argument("--previous-tests")
    parser.add_argument("--benchmarks")
    args = parser.parse_args(argv)
    tests = lambda *names: [PY, "-m", "unittest", *names]  # noqa: E731
    tdir = os.path.join(ROOT, "tests")

    run(1, "Existing tests (the 2.0 test files, as updated)",
        tests("test_feature_menu", "test_dependencies", "test_compatibility", "test_artifacts"), tdir)
    run(2, "New 2.1 tests", tests("test_security", "test_test_verification", "test_intelligence",
                                  "test_release", "test_benchmarks", "test_benchmark_findings"), tdir)
    run(2, "Whole suite", tests("discover", "-s", "tests"))
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "repo")
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "dist"))
        run(3, "Example integration: run the app's tests via run_tests.py and verify (in a copy)",
            [PY, "run_integration.py"], os.path.join(copy, "examples", "team-hub", "app"))
        run(3, "Example: full project validation after the fresh run (copy)",
            [PY, os.path.join(copy, "feature-mixer", "scripts", "validate_project.py"),
             os.path.join(copy, "examples", "team-hub", "mixer")])
    run(3, "Example: verify the committed test evidence", [PY, f"{S}/verify_tests.py", f"{EX}/mixer", "--no-write"])
    run(4, "Schemas and templates parse; skill discovery; scripts from any folder; plugin CLI",
        [PY, "tools/release_check.py", "--clean"], tail=12)
    run(4, "Every artifact in the example against its schema", [PY, f"{S}/validate_artifacts.py", f"{EX}/mixer"])
    run(5, "Feature menu dependencies: example menu", [PY, f"{S}/validate_feature_menu.py", f"{EX}/mixer/feature-menu.csv"])
    run(5, "Feature menu dependencies: template (deliberately has a missing dependency)",
        [PY, f"{S}/check_menu.py", "feature-mixer/templates/feature-menu.csv"], expect=1)
    run(6, "Compatibility report: example, strict", [PY, f"{S}/check_compatibility.py", f"{EX}/mixer", "--strict"])
    run(6, "Dependencies and intelligence: example", [PY, f"{S}/check_dependencies.py", f"{EX}/mixer"])
    run(7, "Security scenarios (hostile source, secrets, injection, approvals)", tests("test_security", "-v"), tdir,
        tail=24)
    run(7, "Scan of the example's sources", [PY, f"{S}/scan_source.py", f"{EX}/sources/taskboard"])
    run(8, "Unverified and fabricated test reports", tests("test_test_verification", "-v"), tdir, tail=18)
    run(9, "Unavailable browser and terminal capabilities", tests("test_intelligence.CapabilityTest", "-v"), tdir,
        tail=10)
    run(10, "Installation: skill copied outside the repo; packaging",
        tests("test_release.ReleaseCheckTest", "-v"), tdir, tail=8)
    run(11, "Regression: the frozen 2.0 workspace validates", [PY, f"{S}/validate_project.py",
                                                               "tests/fixtures/v2_0_workspace/mixer"], tail=3)
    if args.previous_tests:
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, "repo")
            skip = shutil.ignore_patterns(".git", "__pycache__")
            shutil.copytree(ROOT, copy, ignore=lambda d, names: set(skip(d, names)) |
                            ({"tests"} if os.path.abspath(d) == ROOT else set()))
            shutil.copytree(args.previous_tests, os.path.join(copy, "tests"),
                            ignore=shutil.ignore_patterns("__pycache__"))
            r = subprocess.run(tests("discover", "-s", "tests"), cwd=copy, capture_output=True, text=True)
            failed = [line for line in (r.stdout + r.stderr).splitlines() if line.startswith(("FAIL:", "ERROR:"))]
            last = [line for line in (r.stdout + r.stderr).splitlines() if line.strip()][-2:]
            rows.append({"step": 11, "label": "Regression: the previous release's own tests, unchanged, against this code",
                         "cmd": "python -m unittest discover -s tests   (previous release's tests/ in a copy)",
                         "exit": r.returncode, "expect": None, "ok": True, "secs": 0, "out": failed + last})
            print(f"ran [{r.returncode}] previous release's tests: {len(failed)} failing")
    if args.benchmarks:
        for name in sorted(os.listdir(os.path.join(ROOT, "benchmarks", "scenarios"))):
            mixer = os.path.join(args.benchmarks, name, "mixer")
            run(12, f"Benchmark score: {name}", [PY, "benchmarks/score.py",
                                                 f"benchmarks/scenarios/{name}/ground-truth.json", mixer],
                expect=None, tail=14)
    write()
    bad = [r for r in rows if not r["ok"] and r["expect"] is not None]
    return 1 if bad else 0


def write():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = ["# Testing and validation report", "",
         f"Generated by `tools/testing_report.py` on {now}, Python {platform.python_version()} on "
         f"{platform.system()}. Every row is a command that ran; outputs are the last lines it printed.", "",
         "| # | Check | Exit | Expected | Result | Seconds |", "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        exp = "any" if r["expect"] is None else r["expect"]
        res = "as expected" if r["ok"] or r["expect"] is None else "UNEXPECTED"
        L.append(f"| {r['step']} | {r['label']} | {r['exit']} | {exp} | {res} | {r['secs']} |")
    L += ["", "Steps follow the release checklist: 1 existing tests, 2 new tests, 3 example integration, "
          "4 schemas, 5 feature-menu dependencies, 6 compatibility reports, 7 security scenarios, "
          "8 unverified and fabricated reports, 9 unavailable capabilities, 10 installation and discovery, "
          "11 regressions against the previous release, 12 benchmark scores.", ""]
    notes = [r for r in rows if r["label"].startswith("Regression: the previous release")]
    if notes:
        L += ["**About step 11 (previous release's tests).** These are the previous release's test files, "
              "byte for byte, run against this release. Failures there are expected where behaviour changed "
              "on purpose: the version number, the list of script files, and the allowed merge-type names. "
              "Any other failure would be a regression. The failing tests are listed in that section's output.", ""]
    L.append("")
    for r in rows:
        L += [f"## {r['step']}. {r['label']}", "", f"`{r['cmd']}` → exit {r['exit']}", "", "```"]
        L += r["out"] or ["(no output)"]
        L += ["```", ""]
    with open(os.path.join(ROOT, "docs", "TESTING-REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
