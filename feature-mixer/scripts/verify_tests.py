#!/usr/bin/env python3
"""Check an integration report against the evidence of the run it claims.

Usage:
    python3 verify_tests.py MIXER_DIR                    verify the report
    python3 verify_tests.py MIXER_DIR --rerun            run the recorded command again and compare
    python3 verify_tests.py MIXER_DIR --update-baseline  after a clean verification, save the regression baseline

A self-reported "passed" is not proof. A test counts as passed only when:
  - the report has an execution block written by run_tests.py,
  - mixer/test-runs/<run-id>/run.json exists and agrees with that block
    (command, times, exit code, outcome, verdict, fingerprints),
  - the run is in the hash-chained ledger (mixer/test-runs/ledger.jsonl), the
    chain is intact and the ledger's fingerprint of run.json matches,
  - the log and results files exist and their SHA-256 fingerprints match,
  - re-reading the results gives the same counts and the same verdict, and
    the verdict is passed or failed (timed-out, no-tests, inconsistent,
    invalid-results, incomplete and interrupted runs prove nothing),
  - the results file lists that test with the same status, and every test
    in the results file is in the report,
  - the exit code agrees with the failures.
Anything else is "unverified".

Also checks: summary counts, timestamps, that the tested code has not
changed since the run (it compares a fingerprint of the run's folder),
regressions against mixer/test-baseline.json (a test that passed before and
now fails, is missing or did not run), that every acceptance criterion in
design/prd.md (AC01...) has a verified passing test, and that every decision
in compat/resolutions.json that names "verified_by" tests or criteria has
them passing.

Options:
  --evidence-key FILE   check the HMAC signatures run_tests.py wrote with the
                        same key (or set FEATURE_MIXER_EVIDENCE_KEY)
  --evidence-copy DIR   compare the run with the copy kept in DIR
  --rerun [--approval ID]  execute the recorded run again and compare. It
                        runs code, so it needs an approval that covers exactly
                        that run (the original one if it is still valid, or a
                        new one); otherwise nothing runs

Writes mixer/test-verification.json with the verified status of every test
and feature. What it cannot do: tell a genuine log from a carefully forged
one written by something that also controls the ledger and the key.
Fingerprints detect change relative to a fingerprint you trust; they do not
prove the evidence was genuine. --rerun is the real proof.

v2.0 workspaces (project.json format 2): reports without execution evidence
give warnings, and their passes still count, marked unverified.
v2.1 workspaces (format 3): those are errors; missing ledgers, unsigned
runs and code changed since the run are warnings.
v2.2 workspaces (format 4): those are errors too.

Exit codes: 0 verified, 1 problems, 2 unreadable input. Standard library only.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from mixerlib import LEGACY_TEST_STATUS, Report, load_json, load_schema, project_root, schema_errors, workspace_format
import approvals
import evidence
import run_tests


def _format_of(mixer_dir):
    path = os.path.join(mixer_dir, "project.json")
    if os.path.exists(path):
        try:
            return workspace_format(load_json(path))
        except ValueError:
            return 2
    return 2


def _strict_for(mixer_dir):
    return _format_of(mixer_dir) >= 3


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


def verify(mixer_dir, kept=None, strict=None, key_file=None, evidence_copy=None):
    """Return (Report, result dict). result has tests {name: status}, features {id: status}, acceptance."""
    fmt = _format_of(mixer_dir)
    strict = fmt >= 3 if strict is None else strict
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
    if not tests:
        rep.error("integration: the report lists no tests, so it proves nothing")
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
        ok, run_info = _check_execution(mixer_dir, data, execution, verified, rep, fmt, key_file, evidence_copy)
        result["run_id"] = execution.get("run_id")
        result["verdict"] = run_info.get("verdict")
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

    # decisions that name the tests proving them (business rules, role maps, ...)
    res_path = os.path.join(mixer_dir, "compat", "resolutions.json")
    if os.path.exists(res_path):
        try:
            resolutions = load_json(res_path)
        except ValueError as e:
            rep.error(str(e))
            resolutions = {}
        by_short = {}
        for t in tests:
            by_short.setdefault(t["name"].rsplit(".", 1)[-1], []).append(t["name"])
        for cid, res in sorted((resolutions or {}).items()):
            if not isinstance(res, dict):
                continue
            for ref in res.get("verified_by") or []:
                if re.fullmatch(r"AC\d{2,}", ref):
                    ok_ref = covered.get(ref) == "verified"
                else:
                    names_ = [ref] if ref in verified else by_short.get(ref, [])
                    ok_ref = bool(names_) and all(verified.get(n) == "passed" for n in names_)
                if not ok_ref:
                    rep.error(f"integration: decision {cid} names {ref} as its proof, but {ref} has no verified "
                              "passing test")
            result.setdefault("decisions", {})[cid] = "verified" if res.get("verified_by") and not any(
                f"decision {cid} names" in e for e in rep.errors) else ("unproven" if res.get("verified_by") is
                                                                       not None else "no test named")

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


def _demote(verified):
    for n in verified:
        if verified[n] in ("passed", "failed", "skipped"):
            verified[n] = "unverified"


def _check_execution(mixer_dir, data, ex, verified, rep, fmt=3, key_file=None, evidence_copy=None):
    """Check the report's execution block against the run's evidence. Returns (ok, info)."""
    before = len(rep.errors)
    info = {}
    strict_new = fmt >= 4
    soft = rep.error if strict_new else rep.warn
    run_id = str(ex.get("run_id"))
    run_json = os.path.join(mixer_dir, "test-runs", run_id, "run.json")
    if not os.path.exists(run_json):
        rep.error(f"integration: run record test-runs/{run_id}/run.json is missing")
        _demote(verified)
        return False, info
    try:
        record = load_json(run_json)
    except ValueError as e:
        rep.error(f"integration: run record cannot be read ({e})")
        _demote(verified)
        return False, info
    info["verdict"] = record.get("verdict")
    # a run record written by run_tests.py 2.2 carries the newer evidence, so its checks are errors whatever
    # the workspace format; older records (no "format") keep the softer rules of their workspace
    if record.get("format", 1) >= 2:
        strict_new, soft = True, rep.error
    for key in ("started_at", "finished_at", "exit_code", "log", "log_sha256", "results", "results_sha256"):
        if record.get(key) != ex.get(key):
            rep.error(f"integration: report execution.{key} does not match the run record")
    for key in ("outcome", "verdict", "results_status", "code_sha256_after", "approval", "cwd"):
        if key in ex and ex.get(key) is not None and record.get(key) != ex.get(key):
            rep.error(f"integration: report execution.{key} does not match the run record")
    if record.get("command") != data.get("command"):
        rep.error("integration: report command does not match the run record")
    rec_sha = evidence.sha256_file(run_json)
    if ex.get("run_record_sha256") and ex["run_record_sha256"] != rec_sha:
        rep.error("integration: run.json does not match the fingerprint the report recorded for it")
    elif not ex.get("run_record_sha256"):
        soft("integration: the report does not fingerprint its run record (written before run_tests.py 2.2)")
    started, finished = _parse_time(ex.get("started_at")), _parse_time(ex.get("finished_at"))
    if not started or not finished or finished < started:
        rep.error("integration: start and finish times are missing or out of order")
    elif started > datetime.now(timezone.utc) + timedelta(minutes=5):
        rep.error("integration: the run claims to start in the future")

    # ledger: an append-only, hash-chained list of runs
    key = None
    try:
        key, key_id, _ = evidence.load_key(key_file or os.environ.get(run_tests.KEY_ENV), mixer_dir)
    except (ValueError, OSError) as e:
        rep.error(f"integration: evidence key: {e}")
    problems, entries = evidence.check_ledger(mixer_dir, key)
    if problems is None:
        soft("integration: no run ledger (test-runs/ledger.jsonl); runs cannot be checked against a chain")
    else:
        for p in problems:
            rep.error(f"integration: {p}")
        entry = entries.get(run_id)
        if entry is None:
            rep.error(f"integration: run {run_id} is not in the run ledger")
        elif entry.get("run_record_sha256") != rec_sha:
            rep.error(f"integration: run.json for {run_id} was changed after the ledger recorded it")
    if key is not None:
        if not record.get("hmac"):
            rep.error(f"integration: an evidence key was given but run {run_id} is not signed")
        else:
            body = {k: v for k, v in record.items() if k != "hmac"}
            if record.get("evidence_key_id") not in (None, key_id):
                rep.error(f"integration: run {run_id} was signed with a different key ({record.get('evidence_key_id')})")
            elif not evidence.signature_ok(key, body, record["hmac"]):
                rep.error(f"integration: run {run_id}'s signature does not match: the run record was altered")
    elif record.get("hmac"):
        rep.warn("integration: the run is signed; pass --evidence-key to check the signature")

    results = []
    for k in ("log", "results"):
        path = os.path.join(mixer_dir, ex.get(k) or "")
        if not os.path.isfile(path):
            rep.error(f"integration: {k} file {ex.get(k)} is missing")
        elif evidence.sha256_file(path) != ex.get(f"{k}_sha256"):
            rep.error(f"integration: {k} file {ex.get(k)} does not match its recorded fingerprint")
        elif k == "results":
            results, status, rproblems, _ = run_tests.parse_results(path)
            if status in ("missing", "malformed", "too-large"):
                rep.error(f"integration: results file cannot be used ({'; '.join(rproblems)})")
            for p in rproblems if status == "inconsistent" else []:
                rep.error(f"integration: results file contradicts itself: {p}")
            counts = run_tests.counts_of(results)
            verdict, why = run_tests.decide_verdict(record.get("outcome", "exited"), record.get("exit_code"), status,
                                                    counts, record.get("expect_tests"))
            info["recomputed_verdict"] = verdict
            if record.get("verdict") and record["verdict"] != verdict:
                rep.error(f"integration: the run record says verdict {record['verdict']}, but its evidence gives "
                          f"{verdict}")
            if record.get("counts") and record["counts"] != counts:
                rep.error("integration: the run record's test counts do not match its results file")
            if verdict not in ("passed", "failed"):
                rep.error(f"integration: run {run_id} has verdict {verdict} ({'; '.join(why)}): its results "
                          "prove nothing")
    # evidence copy kept elsewhere
    if evidence_copy:
        other = os.path.join(evidence_copy, run_id)
        if not os.path.isdir(other):
            rep.error(f"integration: no copy of run {run_id} in {evidence_copy}")
        else:
            for name in sorted(os.listdir(os.path.join(mixer_dir, "test-runs", run_id))):
                mine = os.path.join(mixer_dir, "test-runs", run_id, name)
                theirs = os.path.join(other, name)
                if not os.path.isfile(theirs) or evidence.sha256_file(theirs) != evidence.sha256_file(mine):
                    rep.error(f"integration: {name} of run {run_id} differs from the copy in {evidence_copy}")
    if len(rep.errors) > before:
        _demote(verified)
        return False, info

    by_id = {}
    for r in results:
        by_id[r["id"]] = r["status"]
        by_id.setdefault(r["name"], r["status"])
    for name, st in list(verified.items()):
        actual = by_id.get(name)
        if st in ("passed", "failed", "skipped", "unverified"):
            if actual is None:
                if st != "unverified":
                    rep.error(f"integration: {name} is reported {st} but is not in the results file")
                verified[name] = "unverified"
            elif actual != st:
                rep.error(f"integration: {name} is reported {st} but the results file says {actual}")
                verified[name] = actual
        elif st == "not-executed" and actual is not None:
            rep.error(f"integration: {name} is reported not-executed but the results file lists it")
    reported = set(verified)
    missing = [r for r in results if r["id"] not in reported and r["name"] not in reported]
    for r in missing:
        if r["status"] == "failed":
            rep.error(f"integration: {r['id']} failed in the results file but is left out of the report")
    if [r for r in missing if r["status"] != "failed"]:
        (rep.error if strict_new else rep.warn)(
            f"integration: {len([r for r in missing if r['status'] != 'failed'])} test(s) in the results file "
            "are not in the report")
    any_failed = any(r["status"] == "failed" for r in results)
    if ex.get("exit_code") == 0 and any_failed:
        rep.error("integration: exit code 0 but the results contain failures")
    if ex.get("exit_code") not in (0, None) and not any_failed:
        rep.error(f"integration: exit code {ex.get('exit_code')} although no test failed; the run is not clean")
        _demote(verified)
    if not ex.get("approval"):
        rep.warn("integration: the run does not reference an approval id for executing the tests")

    # the code the run tested is still the code in the folder
    if record.get("code_sha256_after"):
        cwd = os.path.join(project_root(mixer_dir), record.get("cwd") or ".")
        if os.path.isdir(cwd):
            now_sha, _ = approvals.code_fingerprint(mixer_dir, cwd, record.get("junit"))
            if now_sha != record["code_sha256_after"]:
                msg = (f"integration: the files in {record.get('cwd')} changed after run {run_id}; its results may "
                       "not describe the current code: re-run the tests")
                if strict_new:
                    rep.error(msg)
                    _demote(verified)
                else:
                    rep.warn(msg)
        else:
            rep.error(f"integration: the tested folder {record.get('cwd')} no longer exists")
    elif fmt >= 4:
        rep.error("integration: the run record has no fingerprint of the tested code (run_tests.py 2.2 writes one)")
    return len(rep.errors) == before, info


def rerun(mixer_dir, rep, approval=None, key_file=None):
    data = load_json(os.path.join(mixer_dir, "integration-report.json"))
    ex = data.get("execution") or {}
    record = load_json(os.path.join(mixer_dir, "test-runs", ex.get("run_id", ""), "run.json"))
    cwd = os.path.join(project_root(mixer_dir), record["cwd"])
    ut = record.get("unittest")
    if not ut:
        rep.error("rerun: only unittest-harness runs can be re-run automatically; rerun the command with "
                  "run_tests.py and compare")
        return None
    try:
        new = run_tests.execute(mixer_dir, cwd, [], "unittest", unittest_start=ut["start"], top=ut["top"],
                                approval=approval or record.get("approval"), key_file=key_file,
                                timeout=record.get("timeout_seconds") or run_tests.DEFAULT_TIMEOUT,
                                authorised_by="verify_tests.py --rerun")
    except run_tests.Refused as e:
        rep.error(f"rerun: refused, nothing was run: {e}")
        return None
    fresh = {r["id"]: r["status"] for r in run_tests.parse_results(os.path.join(mixer_dir, new["results"]))[0]}
    if new["verdict"] not in ("passed", "failed"):
        rep.error(f"rerun: the re-run's verdict is {new['verdict']} ({'; '.join(new['verdict_reasons'])})")
    for t in data["tests"]:
        old = LEGACY_TEST_STATUS.get(t["status"], t["status"])
        if old in ("passed", "failed", "skipped") and fresh.get(t["name"]) != old:
            rep.error(f"rerun: {t['name']} was reported {old} but the re-run gives {fresh.get(t['name'], 'missing')}")
    return new["run_id"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify an integration report against its execution evidence.")
    parser.add_argument("mixer_dir")
    parser.add_argument("--rerun", action="store_true", help="execute the recorded run again (needs approval)")
    parser.add_argument("--approval", help="approval id for --rerun (default: the run's own, if still valid)")
    parser.add_argument("--evidence-key", help="HMAC key file used by run_tests.py (kept outside mixer/)")
    parser.add_argument("--evidence-copy", help="folder holding copies of the runs, to compare against")
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
        rep, result = verify(args.mixer_dir, kept, key_file=args.evidence_key, evidence_copy=args.evidence_copy)
        if args.rerun:
            has_run = load_json(os.path.join(args.mixer_dir, "integration-report.json")).get("execution")
            if has_run:
                result["rerun_id"] = rerun(args.mixer_dir, rep, args.approval, args.evidence_key)
            else:
                rep.error("rerun: the report has no recorded run to repeat; run the tests with run_tests.py")
    except (ValueError, KeyError, OSError) as e:
        print(f"error: {e}")
        return 2
    result["errors"] = len(rep.errors)
    result["warnings"] = len(rep.warnings)
    result["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not args.no_write:
        evidence.atomic_write_json(os.path.join(args.mixer_dir, "test-verification.json"), result)
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
