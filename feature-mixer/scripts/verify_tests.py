#!/usr/bin/env python3
"""Check an integration report against the evidence of the run it claims.

Usage:
    python3 verify_tests.py MIXER_DIR                    verify the report
    python3 verify_tests.py MIXER_DIR --rerun            run the recorded command again and compare
    python3 verify_tests.py MIXER_DIR --update-baseline  after a clean verification, save the regression baseline

A self-reported "passed" is not proof. A test counts as passed only when:
  - the report has an execution block written by run_tests.py,
  - mixer/test-runs/<run-id>/run.json exists and agrees with that block
    (command, times, exit code, fingerprints),
  - the log and results files exist and their SHA-256 fingerprints match,
  - the results file lists that test with the same status,
  - the exit code agrees with the failures.
Anything else is "unverified".

Also checks: summary counts, timestamps, regressions against
mixer/test-baseline.json (a test that passed before and now fails, is
missing or did not run), and that every acceptance criterion in
design/prd.md (AC01...) has a verified passing test.

Writes mixer/test-verification.json with the verified status of every test
and feature. What it cannot do: tell a genuine log from a carefully forged
one. --rerun (only with the user's approval, since it executes code) is the
real proof.

v2.0 workspaces (project.json format 2): reports without execution evidence
give warnings, and their passes still count, marked unverified.
v2.1 workspaces (format 3): they are errors and prove nothing.

Exit codes: 0 verified, 1 problems, 2 unreadable input. Standard library only.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from mixerlib import LEGACY_TEST_STATUS, Report, load_json, load_schema, schema_errors, workspace_format
import run_tests


def _strict_for(mixer_dir):
    path = os.path.join(mixer_dir, "project.json")
    if os.path.exists(path):
        try:
            return workspace_format(load_json(path)) >= 3
        except ValueError:
            return False
    return False


def acceptance_ids(mixer_dir):
    path = os.path.join(mixer_dir, "design", "prd.md")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^## Acceptance criteria\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    return sorted(set(re.findall(r"^\|\s*(AC\d{2,})\s*\|", m.group(1), re.M)))


def _parse_time(value):
    try:
        t = datetime.fromisoformat(value)
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def verify(mixer_dir, kept=None, strict=None):
    """Return (Report, result dict). result has tests {name: status}, features {id: status}, acceptance."""
    strict = _strict_for(mixer_dir) if strict is None else strict
    rep = Report()
    result = {"run_id": None, "tests": {}, "features": {}, "acceptance": {}, "verified": False}
    path = os.path.join(mixer_dir, "integration-report.json")
    if not os.path.exists(path):
        rep.error("integration: missing integration-report.json (run the tests with run_tests.py)")
        return rep, result
    try:
        data = load_json(path)
    except ValueError as e:
        rep.error(str(e))
        return rep, result
    for err in schema_errors(data, load_schema("integration-report.schema.json")):
        rep.error(f"integration: integration-report.json {err}")
    if rep.errors:
        return rep, result

    tests = data["tests"]
    names = [t["name"] for t in tests]
    for n in sorted({n for n in names if names.count(n) > 1}):
        rep.error(f"integration: test '{n}' is listed twice")
    status_of = {t["name"]: LEGACY_TEST_STATUS.get(t["status"], t["status"]) for t in tests}

    # summary
    s = data["summary"]
    counts = {k: sum(v == k for v in status_of.values()) for k in ("passed", "failed", "skipped", "not-executed",
                                                                    "unverified")}
    if s["total"] != len(tests) or s["passed"] != counts["passed"] or s["failed"] != counts["failed"] \
            or s["skipped"] != counts["skipped"] \
            or s.get("not_executed", counts["not-executed"]) != counts["not-executed"]:
        rep.error("integration: summary counts do not match the tests listed")

    verified = dict(status_of)
    execution = data.get("execution")
    if not execution:
        verified = {n: ("unverified" if st in ("passed", "failed", "skipped") else st) for n, st in status_of.items()}
        msg = "integration: no execution evidence (no run_tests.py record): every result is reported but unverified"
        (rep.error if strict else rep.warn)(msg)
    else:
        ok = _check_execution(mixer_dir, data, execution, verified, rep)
        result["run_id"] = execution.get("run_id")
        result["verified"] = ok

    for t in tests:
        st = status_of[t["name"]]
        if st == "failed":
            msg = f"integration: failing test {t['name']} ({', '.join(t['features']) or 'no feature'})"
            if t.get("error"):
                msg += f": {t['error'][:160]}"
            rep.error(msg)
            if not t.get("fix"):
                rep.warn(f"integration: failing test {t['name']} has no recommended fix recorded")
        elif st == "not-executed":
            rep.error(f"integration: test {t['name']} did not run ({', '.join(t['features']) or 'no feature'})")

    # feature status: legacy (format 2) passes still count, but are labelled unverified
    proof = {}
    for t in tests:
        st, vst = status_of[t["name"]], verified[t["name"]]
        for f in t["features"]:
            p = proof.setdefault(f, set())
            if vst == "passed":
                p.add("verified")
            elif vst == "failed":
                p.add("failed")
            elif vst == "unverified" and st == "passed" and not strict:
                p.add("unverified-pass")
    feats = {}
    for f, kinds in proof.items():
        feats[f] = "failed" if "failed" in kinds else "verified" if "verified" in kinds else \
            "unverified" if "unverified-pass" in kinds else "untested"
    kept = sorted(kept) if kept is not None else sorted(feats)
    for f in kept:
        st = feats.get(f, "untested")
        if st == "untested" or st == "failed":
            rep.error(f"integration: kept feature {f} has no passing test, so it is not verified")
        elif st == "unverified":
            rep.warn(f"integration: kept feature {f} passes only in a report without execution evidence")
        feats.setdefault(f, st)
    if kept:
        for f in sorted(set(feats) - set(kept)):
            rep.warn(f"integration: tests cover {f}, which is not a kept feature")

    # acceptance criteria
    acs = acceptance_ids(mixer_dir)
    covered = {}
    for t in tests:
        for ac in t.get("acceptance") or []:
            if verified[t["name"]] == "passed":
                covered[ac] = "verified"
    for ac in acs:
        result["acceptance"][ac] = covered.get(ac, "untested")
        if ac not in covered:
            msg = f"integration: acceptance criterion {ac} has no verified passing test"
            (rep.error if strict else rep.warn)(msg)

    # regressions
    base_path = os.path.join(mixer_dir, "test-baseline.json")
    if os.path.exists(base_path):
        base = load_json(base_path).get("tests", {})
        for name, st in sorted(base.items()):
            now_st = verified.get(name, "missing")
            if st == "passed" and now_st != "passed":
                rep.error(f"integration: regression: {name} passed in the baseline but is now {now_st}")

    result["tests"] = verified
    result["features"] = feats
    return rep, result


def _check_execution(mixer_dir, data, ex, verified, rep):
    before = len(rep.errors)
    run_json = os.path.join(mixer_dir, "test-runs", str(ex.get("run_id")), "run.json")
    if not os.path.exists(run_json):
        rep.error(f"integration: run record test-runs/{ex.get('run_id')}/run.json is missing")
        for n in verified:
            if verified[n] in ("passed", "failed", "skipped"):
                verified[n] = "unverified"
        return False
    record = load_json(run_json)
    for key in ("started_at", "finished_at", "exit_code", "log", "log_sha256", "results", "results_sha256"):
        if record.get(key) != ex.get(key):
            rep.error(f"integration: report execution.{key} does not match the run record")
    if record.get("command") != data.get("command"):
        rep.error("integration: report command does not match the run record")
    started, finished = _parse_time(ex.get("started_at")), _parse_time(ex.get("finished_at"))
    if not started or not finished or finished < started:
        rep.error("integration: start and finish times are missing or out of order")
    elif started > datetime.now(timezone.utc) + timedelta(minutes=5):
        rep.error("integration: the run claims to start in the future")

    results = []
    for key in ("log", "results"):
        path = os.path.join(mixer_dir, ex.get(key) or "")
        if not os.path.isfile(path):
            rep.error(f"integration: {key} file {ex.get(key)} is missing")
        elif run_tests.sha256(path) != ex.get(f"{key}_sha256"):
            rep.error(f"integration: {key} file {ex.get(key)} does not match its recorded fingerprint")
        elif key == "results":
            try:
                results = run_tests.parse_junit(path)
            except Exception as e:  # malformed XML
                rep.error(f"integration: results file cannot be read ({e})")
    if len(rep.errors) > before:
        for n in verified:
            if verified[n] in ("passed", "failed", "skipped"):
                verified[n] = "unverified"
        return False

    by_id = {}
    for r in results:
        by_id[r["id"]] = r["status"]
        by_id.setdefault(r["name"], r["status"])
    for name, st in list(verified.items()):
        actual = by_id.get(name)
        if st in ("passed", "failed", "skipped"):
            if actual is None:
                rep.error(f"integration: {name} is reported {st} but is not in the results file")
                verified[name] = "unverified"
            elif actual != st:
                rep.error(f"integration: {name} is reported {st} but the results file says {actual}")
                verified[name] = actual
        elif st == "not-executed" and actual is not None:
            rep.error(f"integration: {name} is reported not-executed but the results file lists it")
    reported = set(verified)
    missing = [r["id"] for r in results if r["id"] not in reported and r["name"] not in reported]
    if missing:
        rep.warn(f"integration: {len(missing)} test(s) in the results file are not in the report")
    any_failed = any(r["status"] == "failed" for r in results)
    if ex.get("exit_code") == 0 and any_failed:
        rep.error("integration: exit code 0 but the results contain failures")
    if ex.get("exit_code") not in (0, None) and not any_failed:
        rep.warn(f"integration: exit code {ex.get('exit_code')} although no test failed; check the log")
    if not ex.get("approval"):
        rep.warn("integration: the run does not reference an approval id for executing the tests")
    return len(rep.errors) == before


def rerun(mixer_dir, rep):
    data = load_json(os.path.join(mixer_dir, "integration-report.json"))
    ex = data.get("execution") or {}
    record = load_json(os.path.join(mixer_dir, "test-runs", ex.get("run_id", ""), "run.json"))
    cwd = os.path.join(os.path.dirname(os.path.abspath(mixer_dir)), record["cwd"])
    ut = record.get("unittest")
    if ut:
        new = run_tests.execute(mixer_dir, cwd, [], "unittest", unittest_start=ut["start"], top=ut["top"],
                                approval=record.get("approval"))
    else:
        rep.error("rerun: only unittest-harness runs can be re-run automatically; rerun the command with "
                  "run_tests.py and compare")
        return None
    fresh = {r["id"]: r["status"] for r in run_tests.parse_junit(os.path.join(mixer_dir, new["results"]))}
    for t in data["tests"]:
        old = LEGACY_TEST_STATUS.get(t["status"], t["status"])
        if old in ("passed", "failed", "skipped") and fresh.get(t["name"]) != old:
            rep.error(f"rerun: {t['name']} was reported {old} but the re-run gives {fresh.get(t['name'], 'missing')}")
    return new["run_id"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify an integration report against its execution evidence.")
    parser.add_argument("mixer_dir")
    parser.add_argument("--rerun", action="store_true", help="execute the recorded run again (needs approval)")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true", help="do not write test-verification.json")
    args = parser.parse_args(argv)
    if not os.path.isdir(args.mixer_dir):
        print(f"error: not a folder: {args.mixer_dir}")
        return 2
    kept = None
    menu = os.path.join(args.mixer_dir, "feature-menu.csv")
    if os.path.exists(menu):
        from validate_feature_menu import load
        kept = {r["id"] for r in load(menu) if r.get("pick", "").lower() == "keep"}
    try:
        rep, result = verify(args.mixer_dir, kept)
        if args.rerun:
            has_run = load_json(os.path.join(args.mixer_dir, "integration-report.json")).get("execution")
            if has_run:
                result["rerun_id"] = rerun(args.mixer_dir, rep)
            else:
                rep.error("rerun: the report has no recorded run to repeat; run the tests with run_tests.py")
    except (ValueError, KeyError, OSError) as e:
        print(f"error: {e}")
        return 2
    result["errors"] = len(rep.errors)
    result["warnings"] = len(rep.warnings)
    result["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not args.no_write:
        with open(os.path.join(args.mixer_dir, "test-verification.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    if args.update_baseline:
        if rep.errors:
            print("baseline not updated: verification has errors")
        else:
            with open(os.path.join(args.mixer_dir, "test-baseline.json"), "w", encoding="utf-8") as f:
                json.dump({"run_id": result["run_id"], "tests": result["tests"]}, f, indent=2)
                f.write("\n")
            print("baseline updated")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        counts = {}
        for st in result["tests"].values():
            counts[st] = counts.get(st, 0) + 1
        print("tests: " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"))
        fs = {}
        for st in result["features"].values():
            fs[st] = fs.get(st, 0) + 1
        print("features: " + (", ".join(f"{k} {v}" for k, v in sorted(fs.items())) or "none"))
        for line in rep.lines():
            print(line)
        if not rep.errors:
            print("the report matches its execution evidence")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
