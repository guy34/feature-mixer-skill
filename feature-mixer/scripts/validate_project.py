#!/usr/bin/env python3
"""Validate a whole Feature Mixer workspace and check phase completion.

Usage:
    python3 validate_project.py MIXER_DIR                  check every phase up to the current one
    python3 validate_project.py MIXER_DIR --phase PHASE    check that PHASE (and what it needs) is complete

Phases, in order: recon, extraction, selection, compatibility, architecture,
implementation, integration, deployment.

What it checks:
  project      project.json schema, unique app ids, phase order, approvals,
               checkpoints, failed phases (and where to roll back to)
  recon        every source folder: report.md + source.json (validate_artifacts)
  extraction   the feature menu loads; evidence refs and source features exist
               in the source reports and belong to the right app
  selection    no undecided rows, something kept, menu valid, reuse/adapt only
               where the source's licence allows it, user approval
  compatibility no unresolved critical conflict, every high conflict decided
               and approved, destructive migrations approved, user approval
  architecture prd.md, architecture.md, architecture.json valid and complete,
               user approval
  implementation  every roadmap slice done, target folder exists
  integration  every kept feature proven by a passing test, no failures
  deployment   explicit user approval (never automatic)

v2.1 additions (errors in format 3 workspaces, warnings in format 2):
  capabilities mixer/capabilities.json recorded before recon, Claude's own
               tools decided, and no evidence that needed a missing tool
  security     a security-scan.json for every source with code, high
               findings acknowledged; an approvals ledger whose entries
               back the test run, migrations and deployment
  large repos  index-based coverage, module summaries, no stale features
  merging      merge-plan.json consistent with the menu and the tests
  architecture style chosen with alternatives and its own rules
  tests        verified execution evidence (verify_tests.py)
  secrets      no credential in any mixer/ file (an error in every format)

Exit codes: 0 ready, 1 something to fix, 2 unreadable workspace.
Standard library only, no network.
"""

import argparse
import os
import sys

import check_compatibility
import validate_artifacts
from mixerlib import (
    APP_ID, APPROVAL_PHASES, CHECKPOINT_PHASES, EVIDENCE_REF, PHASES, Report, app_ids_for,
    blocking, load_json, load_schema, project_root, schema_errors, source_dir, split_ids, workspace_format,
)

CODE_INPUTS = ("local-directory", "github", "source-code")
CLAUDE_CAPS = ("browser", "web_fetch", "repository_access", "external_api")
from validate_feature_menu import load_menu, validate


def phase_status(project, phase):
    return (project.get("phases", {}).get(phase) or {}).get("status", "pending")


def check_project(project):
    rep = Report()
    for err in schema_errors(project, load_schema("project.schema.json")):
        rep.error(f"project.json {err}")
    if rep.errors:
        return rep
    ids = [s["id"] for s in project["sources"]]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        rep.error(f"project.json: app id {i} is used twice")
    slugs = [s["slug"] for s in project["sources"]]
    for s in sorted({s for s in slugs if slugs.count(s) > 1}):
        rep.error(f"project.json: slug {s} is used twice")

    statuses = [phase_status(project, p) for p in PHASES]
    for i, p in enumerate(PHASES):
        if statuses[i] in ("in-progress", "done"):
            for q in PHASES[:i]:
                if phase_status(project, q) != "done":
                    rep.error(f"{p} is {statuses[i]} but {q} is {phase_status(project, q)}: phases run in order")
                    break
        if statuses[i] == "done" and p in APPROVAL_PHASES and project["phases"][p].get("approved") is not True:
            rep.error(f"{p} is done but not approved by the user")

    ap_ids = [a["id"] for a in project.get("approvals", [])]
    for a in sorted({a for a in ap_ids if ap_ids.count(a) > 1}):
        rep.error(f"approval {a} is listed twice")

    cps = project.get("checkpoints", [])
    cp_ids = [c["id"] for c in cps]
    for c in sorted({c for c in cp_ids if cp_ids.count(c) > 1}):
        rep.error(f"checkpoint {c} is listed twice")
    for p in CHECKPOINT_PHASES:
        if phase_status(project, p) == "done" and not any(c["phase"] == p for c in cps):
            rep.warn(f"{p} is done but has no checkpoint to roll back to")

    for i, p in enumerate(PHASES):
        if statuses[i] == "failed":
            earlier = [c for c in cps if PHASES.index(c["phase"]) < i]
            if earlier:
                last = earlier[-1]
                rep.error(f"{p} failed: fix it and rerun, or roll back to checkpoint {last['id']} "
                          f"({last['phase']}, {last['ref']}); then set {p} to in-progress")
            else:
                rep.error(f"{p} failed and there is no earlier checkpoint; fix it and rerun")
        elif statuses[i] == "rolled-back":
            rep.warn(f"{p} was rolled back; set it to in-progress when the next attempt starts")
    return rep


def current_phase(project):
    reached = [p for p in PHASES if phase_status(project, p) != "pending"]
    return reached[-1] if reached else PHASES[0]


def load_capabilities(mixer_dir, project, rep, strict):
    path = os.path.join(mixer_dir, "capabilities.json")
    flag = rep.error if strict else rep.warn
    if not os.path.exists(path):
        flag("capabilities: missing capabilities.json; run check_environment.py before reconnaissance")
        return None
    data = load_json(path)
    for err in schema_errors(data, load_schema("capabilities.schema.json")):
        rep.error(f"capabilities: {err}")
        return None
    caps = data["capabilities"]
    if phase_status(project, "recon") == "done":
        for c in CLAUDE_CAPS:
            if caps.get(c, {}).get("status") == "not-checked":
                flag(f"capabilities: '{c}' is still not-checked; record what the session really had")
    return caps


def check_recon(mixer_dir, project):
    rep = Report()
    strict = workspace_format(project) >= 3
    caps = load_capabilities(mixer_dir, project, rep, strict)
    for s in project["sources"]:
        folder = source_dir(mixer_dir, s)
        if not os.path.isdir(folder):
            rep.error(f"recon: no folder for {s['id']} ({s['name']}); expected {os.path.relpath(folder, mixer_dir)}")
            continue
        has_code = s.get("local_path") or any(i["kind"] in CODE_INPUTS for i in s["inputs"])
        if has_code and not os.path.exists(os.path.join(folder, "security-scan.json")):
            (rep.error if strict else rep.warn)(
                f"recon: {s['id']} ({s['name']}) has code but no security-scan.json; run scan_source.py before reading it")
        rep.merge(validate_artifacts.check_source(folder, s["id"], strict=strict, capabilities=caps,
                                                  access=s.get("access"), fmt=workspace_format(project)))
    return rep


def _sources(mixer_dir, project):
    out = {}
    for s in project["sources"]:
        path = os.path.join(source_dir(mixer_dir, s), "source.json")
        if os.path.exists(path):
            try:
                out[s["id"]] = load_json(path)
            except ValueError:
                pass
    return out


def check_extraction(mixer_dir, project):
    rep = Report()
    path = os.path.join(mixer_dir, "feature-menu.csv")
    if not os.path.exists(path):
        rep.error("extraction: missing feature-menu.csv")
        return rep, None, None
    try:
        header, rows = load_menu(path)
    except ValueError as e:
        rep.error(f"extraction: feature-menu.csv {e}")
        return rep, None, None
    reports = _sources(mixer_dir, project)
    evidence = {e["id"]: app for app, r in reports.items() for e in r.get("evidence", [])}
    features = {f["id"]: app for app, r in reports.items() for f in r.get("features", [])}
    mentioned = set()
    for r in rows:
        if not r.get("id"):
            continue
        apps = app_ids_for(r.get("source_app"), project)
        for a in apps:
            if not APP_ID.match(a):
                rep.error(f"extraction: {r['id']} names source '{a}', which is not an app in project.json")
        for ref in split_ids(r.get("evidence_refs")):
            if EVIDENCE_REF.match(ref) and ref not in evidence:
                rep.error(f"extraction: {r['id']} cites evidence {ref}, which is not in any source report")
            elif ref in evidence and apps and evidence[ref] not in apps:
                rep.warn(f"extraction: {r['id']} cites {ref} from app {evidence[ref]} but its source_app is "
                         f"{r.get('source_app')}")
        for f in split_ids(r.get("source_features")):
            mentioned.add(f)
            if f not in features:
                rep.error(f"extraction: {r['id']} maps to source feature {f}, which no report contains")
    if "source_features" in header:
        missing = sorted(set(features) - mentioned)
        if missing:
            rep.warn("extraction: source features not on the menu: " + ", ".join(missing))
    return rep, header, rows


def check_selection(mixer_dir, project, header, rows):
    rep = Report()
    if rows is None:
        rep.error("selection: no feature menu to select from")
        return rep
    real = [r for r in rows if r.get("id")]
    undecided = [r["id"] for r in real if not r.get("pick", "").strip()]
    if undecided:
        rep.error(f"selection: {len(undecided)} feature(s) still undecided: {', '.join(undecided)}")
    kept = [r for r in real if r.get("pick", "").lower() == "keep"]
    if not kept:
        rep.error("selection: nothing is kept")
    rep.merge(validate(rows, header), "selection: ")
    reuse = {s["id"]: s for s in project["sources"]}
    for r in kept:
        strat = r.get("implementation_strategy", "").lower()
        if strat in ("reuse", "adapt"):
            for a in app_ids_for(r.get("source_app"), project):
                s = reuse.get(a)
                if s and s["code_reuse"] != "allowed":
                    rep.error(f"selection: {r['id']} ({r['feature']}) uses '{strat}', which copies code from "
                              f"{a} ({s['name']}), but code_reuse there is '{s['code_reuse']}': use rebuild or combine")
    return rep


def check_compat(mixer_dir, project=None):
    rep = Report()
    project = project or {}
    try:
        report = check_compatibility.run(mixer_dir)
    except (OSError, ValueError, KeyError) as e:
        rep.error(f"compatibility: could not run the analysis ({e})")
        return rep
    for c in blocking(report["conflicts"], strict=False):
        rep.error(f"compatibility: critical conflict {c['id']} is {c['status']}: {c['detail']}")
    for c in report["conflicts"]:
        if c["severity"] == "high" and c["status"] != "resolved":
            rep.error(f"compatibility: high conflict {c['id']} is {c['status']}; record a decision the user approved")
    ledger = {a["target"] for a in project.get("approvals", []) if a["action"] == "migration" and a["approved"]}
    for m in check_compatibility.unapproved_migrations(report):
        if m["id"] not in ledger:
            rep.error(f"compatibility: destructive migration {m['id']} needs explicit approval")
    opened = [c["id"] for c in report["conflicts"] if c["status"] == "open" and c["severity"] in ("medium", "low")]
    if opened:
        rep.warn(f"compatibility: {len(opened)} medium/low conflict(s) without a recorded decision")
    if not os.path.exists(os.path.join(mixer_dir, "compat", "compatibility-report.json")):
        rep.warn("compatibility: run check_compatibility.py --write so the report is saved")
    return rep


def check_test_approval(mixer_dir, project):
    rep = Report()
    path = os.path.join(mixer_dir, "integration-report.json")
    if not os.path.exists(path) or workspace_format(project) < 3:
        return rep
    ex = load_json(path).get("execution") or {}
    ref = ex.get("approval")
    ledger = {a["id"]: a for a in project.get("approvals", [])}
    if not ref:
        rep.error("integration: the test run does not reference an approval; record the user's approval "
                  "(action run-tests) and pass --approval to run_tests.py")
    elif ref not in ledger:
        rep.error(f"integration: the test run cites approval {ref}, which is not in project.json")
    elif not ledger[ref]["approved"] or ledger[ref]["action"] not in ("run-tests", "run-source-code"):
        rep.error(f"integration: approval {ref} does not approve running tests")
    else:
        scope = ledger[ref].get("scope")
        if scope is None:
            (rep.error if workspace_format(project) >= 4 else rep.warn)(
                f"integration: approval {ref} has no scope, so nothing shows it covered the command that ran "
                "(record approvals with approvals.py grant)")
        elif scope.get("cwd") != ex.get("cwd"):
            rep.error(f"integration: approval {ref} covers the folder {scope.get('cwd')}, but the run was in "
                      f"{ex.get('cwd')}")
        log = os.path.join(mixer_dir, "approval-log.jsonl")
        if scope is not None and os.path.exists(log):
            with open(log, encoding="utf-8") as f:
                accepted = [x for x in f if f'"approval": "{ref}"' in x and '"decision": "accepted"' in x]
            if not accepted:
                rep.error(f"integration: approval-log.jsonl has no accepted use of {ref}, so the run did not go "
                          "through run_tests.py's approval check")
    return rep


def check_implementation(mixer_dir, project):
    rep = Report()
    status = validate_artifacts.slices_status(mixer_dir)
    if status is None:
        rep.error("implementation: no architecture.json roadmap")
    else:
        for sid, st in sorted(status.items()):
            if st != "done":
                rep.error(f"implementation: slice {sid} is {st}")
    target = (project.get("target") or {}).get("path")
    if not target:
        rep.error("implementation: project.json has no target.path for the unified app")
    elif not os.path.isdir(os.path.join(project_root(mixer_dir), target)):
        rep.error(f"implementation: target folder {target} does not exist")
    return rep


def check_approved_unchanged(mixer_dir, project):
    """An approved phase's decisions may not change without a new approval (v2.2)."""
    import approvals
    rep = Report()
    fmt = workspace_format(project)
    for p in APPROVAL_PHASES:
        entry = (project.get("phases") or {}).get(p) or {}
        if entry.get("approved") is not True or p == "deployment":
            continue
        want = entry.get("approved_fingerprint")
        if not want:
            if fmt >= 4:
                rep.error(f"{p}: approved without a record of what was approved; record approvals with "
                          f"approvals.py approve-phase --phase {p}")
            continue
        if approvals.phase_fingerprint(mixer_dir, p, entry.get("approved_fingerprint_method", 1)) != want:
            rep.error(f"{p}: changed after the user approved it ({', '.join(approvals.PHASE_FILES[p])}); show the "
                      f"change to the user, log it, and approve the phase again (approvals.py approve-phase "
                      f"--phase {p}); later phases built on the old decision must be redone")
    if project.get("mode") == "plan":
        for p in ("implementation", "integration", "deployment"):
            if phase_status(project, p) not in ("pending",):
                rep.error(f"{p}: the run is in plan mode, which builds nothing, but {p} is "
                          f"{phase_status(project, p)}")
    return rep


def check_journeys(mixer_dir, project):
    """Unit tests can pass while the workflow is broken: at least one end-to-end journey test must pass (v2.2)."""
    rep = Report()
    if workspace_format(project) < 4:
        return rep
    path = os.path.join(mixer_dir, "integration-report.json")
    if not os.path.exists(path):
        return rep
    data = load_json(path)
    journeys = [t for t in data.get("tests", []) if t.get("level") == "journey"]
    if not journeys:
        rep.error("integration: no journey-level test (level: journey): unit and API tests can pass while the "
                  "end-to-end workflow is broken; add at least one test of the core loop")
    elif not any(t.get("status") == "passed" for t in journeys):
        rep.error("integration: no journey-level test passed")
    return rep


def run(mixer_dir, phase=None):
    rep = Report()
    path = os.path.join(mixer_dir, "project.json")
    project = load_json(path)
    proj_rep = check_project(project)
    rep.merge(proj_rep)
    if proj_rep.errors and not project.get("sources"):
        return rep, None
    target = phase or current_phase(project)
    upto = PHASES[:PHASES.index(target) + 1]

    header = rows = None
    kept = set()
    strict = workspace_format(project) >= 3
    rep.merge(validate_artifacts.check_secrets(mixer_dir))
    rep.merge(check_approved_unchanged(mixer_dir, project))
    for p in upto:
        if p == "recon":
            rep.merge(check_recon(mixer_dir, project))
        elif p == "extraction":
            sub, header, rows = check_extraction(mixer_dir, project)
            rep.merge(sub)
        elif p == "selection":
            rep.merge(check_selection(mixer_dir, project, header, rows))
            kept = {r["id"] for r in rows or [] if r.get("id") and r.get("pick", "").lower() == "keep"}
        elif p == "compatibility":
            rep.merge(check_compat(mixer_dir, project))
        elif p == "architecture":
            rep.merge(validate_artifacts.check_design(mixer_dir, kept, strict))
        elif p == "implementation":
            rep.merge(check_implementation(mixer_dir, project))
        elif p == "integration":
            rep.merge(validate_artifacts.check_integration(mixer_dir, kept, strict))
            rep.merge(check_test_approval(mixer_dir, project))
            rep.merge(check_journeys(mixer_dir, project))
        elif p == "deployment":
            if (project["phases"].get("deployment") or {}).get("approved") is not True:
                rep.error("deployment: needs the user's explicit approval in project.json before anything ships")
            elif strict and not any(a["action"] == "deployment" and a["approved"]
                                    for a in project.get("approvals", [])):
                rep.error("deployment: no approval of action 'deployment' in the approvals ledger")
        if p in APPROVAL_PHASES and p != "deployment" and phase_status(project, p) != "pending":
            if (project["phases"].get(p) or {}).get("approved") is not True:
                rep.warn(f"{p}: waiting for the user's approval")
    return rep, target


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a Feature Mixer workspace.")
    parser.add_argument("mixer_dir")
    parser.add_argument("--phase", choices=PHASES)
    args = parser.parse_args(argv)
    if not os.path.exists(os.path.join(args.mixer_dir, "project.json")):
        print(f"error: {args.mixer_dir} has no project.json")
        return 2
    try:
        rep, target = run(args.mixer_dir, args.phase)
    except ValueError as e:
        print(f"error: {e}")
        return 2
    print(f"checked up to: {target or 'project.json'}")
    for line in rep.lines():
        print(line)
    if rep.ok:
        print(f"{target} is complete and valid")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
