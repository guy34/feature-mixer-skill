#!/usr/bin/env python3
"""Check the files Feature Mixer writes.

Usage:
    python3 validate_artifacts.py MIXER_DIR             every artifact that exists
    python3 validate_artifacts.py --source DIR          one source folder

Source reports: required sections; schema; ids unique and prefixed with the
app id; every evidence reference resolves; every feature has evidence;
nothing inferred or unknown is high confidence or claims more than its
evidence; partial coverage lists its unknowns; workflow steps and routes
point at real screens. With an index.json (large repositories): every
module is analysed or skipped with a reason before coverage is "complete",
analysed modules have a summary, evidence points at indexed files, and no
feature is stale. With capabilities: no evidence that needed a tool the
session did not have. With a security scan: high findings acknowledged.

Design: prd.md and architecture.md sections; architecture.json schema;
modules unique and acyclic, each entity owned once; every kept feature in a
module and a slice; no duplicate routes or endpoints; the architecture style
recorded with the alternatives considered and its own consistency rules;
merge-plan.json: every kept feature in exactly one unified feature, groups
merged the way their merge type says, no duplicate functionality.

Integration: delegated to verify_tests.py (execution evidence, statuses,
regressions, acceptance criteria) and the report's sections.

Secrets: no credential pattern anywhere in mixer/.

v2.0 workspaces (project.json format 2) get warnings for the v2.1 checks;
v2.1 workspaces (format 3) get errors.
Exit codes: 0 valid, 1 something to fix, 2 bad input. Standard library only.
"""

import argparse
import os
import re
import sys

from mixerlib import (
    BASIS_RANK, EVIDENCE_REF, FEATURE_REF, SCREEN_REF, SOURCE_REF, WORKFLOW_REF, find_secrets,
    Report, canonical_merge_type, find_cycles, load_json, load_schema, schema_errors, split_ids, workspace_format,
)

REPORT_SECTIONS = ["## Summary", "## Sources used", "## Evidence", "## Features", "## Data model",
                   "## Unknowns"]
PRD_SECTIONS = ["## Problem", "## Users", "## Core loop", "## Features", "## User journeys",
                "## Acceptance criteria", "## Out of scope"]
ARCH_SECTIONS = ["## Stack", "## Modules", "## Data model", "## Authentication and authorization",
                 "## API", "## Navigation", "## Design system", "## Configuration", "## Roadmap"]
INTEGRATION_SECTIONS = ["## Summary", "## Results", "## Failures and fixes"]

# Which capability a kind of source needs before anything read from it is believable.
NEEDS = {"website": ("browser", "web_fetch"), "own-account": ("browser",), "github": ("repository_access",)}
USABLE = ("available", "partial")


def _flag(rep, strict, msg):
    (rep.error if strict else rep.warn)(msg)


def _sections(path, required, rep, label):
    if not os.path.exists(path):
        rep.error(f"{label}: missing {os.path.basename(path)}")
        return
    with open(path, encoding="utf-8") as f:
        text = f.read()
    heads = {line.strip().lower() for line in text.splitlines() if line.startswith("## ")}
    for s in required:
        if s.lower() not in heads:
            rep.error(f"{label}: {os.path.basename(path)} has no '{s}' section")


def summary_name(module):
    return "_root" if module == "(root)" else module.replace("/", "__")


CODE_KINDS = ("local-directory", "github", "source-code")
SINGULAR = {"screens": "screen", "workflows": "workflow", "entities": "entity", "endpoints": "endpoint",
            "rules": "rule", "integrations": "integration"}


def check_source(folder, expected_id=None, strict=False, capabilities=None, access=None, fmt=None):
    """Validate one mixer/sources/<id>-<slug> folder. access (own-code, open-source, closed) and fmt (the
    workspace format) turn on the v2.2 honesty checks: errors in format 4, warnings before."""
    rep = Report()
    name = os.path.basename(os.path.normpath(folder))
    label = f"source {name}"
    m = re.match(r"^([A-Z]{1,3})-[a-z0-9][a-z0-9-]*$", name)
    if not m:
        rep.error(f"{label}: folder should be named <APP-ID>-<slug>, like A-taskboard")
    folder_id = m.group(1) if m else None

    _sections(os.path.join(folder, "report.md"), REPORT_SECTIONS, rep, label)

    path = os.path.join(folder, "source.json")
    if not os.path.exists(path):
        rep.error(f"{label}: missing source.json")
        return rep
    try:
        data = load_json(path)
    except ValueError as e:
        rep.error(str(e))
        return rep
    for err in schema_errors(data, load_schema("source-report.schema.json")):
        rep.error(f"{label}: source.json {err}")
    if rep.errors:
        return rep

    app = data["app"]["id"]
    for want, why in ((folder_id, "folder name"), (expected_id, "project.json")):
        if want and app != want:
            rep.error(f"{label}: source.json says app {app} but the {why} says {want}")

    def unique(items, key, pattern, kind):
        seen = set()
        for item in items:
            v = item.get(key, "")
            if v in seen:
                rep.error(f"{label}: duplicate {kind} id {v}")
            seen.add(v)
            mm = pattern.match(v)
            if mm and mm.group(1) != app:
                rep.error(f"{label}: {kind} id {v} does not start with {app}-")
        return seen

    refs = unique(data["sources_used"], "ref", SOURCE_REF, "source")
    evidence = {e["id"]: e for e in data["evidence"]}
    unique(data["evidence"], "id", EVIDENCE_REF, "evidence")
    screens = unique(data.get("screens", []), "id", SCREEN_REF, "screen")
    unique(data.get("workflows", []), "id", WORKFLOW_REF, "workflow")
    features = unique(data["features"], "id", FEATURE_REF, "feature")

    for e in data["evidence"]:
        if e["source"] not in refs:
            rep.error(f"{label}: evidence {e['id']} cites {e['source']}, which is not in sources_used")

    def resolve(owner, ev_list):
        for ref in ev_list or []:
            if ref not in evidence:
                rep.error(f"{label}: {owner} cites evidence {ref}, which does not exist")

    for f in data["features"]:
        owner = f"{f['id']} ({f['name']})"
        if not f.get("evidence"):
            rep.error(f"{label}: {owner} has no evidence")
        resolve(owner, f.get("evidence"))
        if f["basis"] in ("inferred", "unknown") and f["confidence"] == "high":
            rep.error(f"{label}: {owner} is {f['basis']} but marked high confidence")
        known = [evidence[r]["basis"] for r in f.get("evidence", []) if r in evidence]
        if known and BASIS_RANK[f["basis"]] > max(BASIS_RANK[b] for b in known):
            rep.error(f"{label}: {owner} claims '{f['basis']}' but its evidence is only "
                      f"{'/'.join(sorted(set(known)))}")
        for dep in f.get("depends_on", []):
            if dep not in features:
                rep.error(f"{label}: {owner} depends on {dep}, which is not a feature of {app}")
    for kind in ("screens", "workflows", "entities", "endpoints", "rules", "integrations"):
        for item in data.get(kind, []):
            owner = item.get("id") or item.get("name") or f"{item.get('method', '')} {item.get('path', '')}".strip() \
                or item.get("key")
            resolve(f"{SINGULAR[kind]} {owner}", item.get("evidence"))
            for f in item.get("features", []):
                if f not in features:
                    rep.error(f"{label}: {SINGULAR[kind]} {owner} links to {f}, which is not a feature of {app}")
    for key in ("auth", "architecture"):
        if data.get(key):
            resolve(key, data[key].get("evidence"))
    for w in data.get("workflows", []):
        for step in w["steps"]:
            if step not in screens:
                rep.error(f"{label}: workflow {w['id']} goes through {step}, which is not a listed screen")
    for r in data.get("routes", []):
        if r.get("screen") and r["screen"] not in screens:
            rep.error(f"{label}: route {r['path']} points at {r['screen']}, which is not a listed screen")

    if data["coverage"] == "partial":
        if not data["unknowns"]:
            rep.error(f"{label}: coverage is partial but unknowns is empty; say what could not be found")
        else:
            rep.warn(f"{label}: partial coverage, {len(data['unknowns'])} unknown(s) recorded")
    weak = [f["id"] for f in data["features"] if f["confidence"] == "low"]
    if weak:
        rep.warn(f"{label}: low-confidence features {', '.join(weak)}; verify before relying on them")

    if capabilities is not None:
        _check_capabilities(data, capabilities, rep, label)
    _check_honesty(data, evidence, access, (fmt or (3 if strict else 2)) >= 4, rep, label)
    _check_index(folder, data, rep, label, strict)
    _check_scan(folder, rep, label, strict)
    return rep


def _check_honesty(data, evidence, access, strict, rep, label):
    """Observed, documented and inferred stay apart (v2.2)."""
    say = rep.error if strict else rep.warn
    kinds = {x["ref"]: x["kind"] for x in data["sources_used"]}
    for f in data["features"]:
        bases = {evidence[r]["basis"] for r in f.get("evidence", []) if r in evidence}
        if f["basis"] == "observed" and bases and "observed" not in bases:
            say(f"{label}: {f['id']} ({f['name']}) claims 'observed' but its evidence is only "
                f"{'/'.join(sorted(bases))}: documentation describes behaviour, it does not show it")
    if access == "closed":
        for e in data["evidence"]:
            if kinds.get(e["source"]) in CODE_KINDS:
                say(f"{label}: closed source, but evidence {e['id']} cites code ({kinds[e['source']]}); a closed "
                    "product's code is not available to read")
        for kind in ("entities", "endpoints"):
            for item in data.get(kind, []):
                if item.get("basis") == "observed":
                    bases = {kinds.get(evidence[r]["source"]) for r in item.get("evidence", []) if r in evidence}
                    if not bases & {"own-account", "website", "screenshots"}:
                        name = item.get("name") or f"{item.get('method', '')} {item.get('path', '')}".strip()
                        say(f"{label}: closed source, but {SINGULAR[kind]} {name} is marked observed without anything "
                            "seen in the running product; its backend was not inspected (use documented or "
                            "inferred)")
    contradicted = set()
    for c in data.get("contradictions", []) or []:
        for role in ("documented", "observed"):
            ref = c.get(role)
            if ref not in evidence:
                rep.error(f"{label}: contradiction {c.get('id')} cites {role} evidence {ref}, which does not exist")
        if c.get("documented") in evidence:
            contradicted.add(c["documented"])
        if not str(c.get("resolution") or "").strip():
            say(f"{label}: contradiction {c.get('id')} has no resolution (what the code does wins, or the user "
                "was asked)")
    for f in data["features"]:
        refs = [r for r in f.get("evidence", []) if r in evidence]
        if refs and set(refs) <= contradicted:
            say(f"{label}: {f['id']} ({f['name']}) rests only on documentation the source's code contradicts")


def _check_capabilities(data, caps, rep, label):
    used_kinds = {s["ref"]: s["kind"] for s in data["sources_used"]}
    cited = {e["source"] for e in data["evidence"]}
    for ref, kind in sorted(used_kinds.items()):
        need = NEEDS.get(kind)
        if not need or ref not in cited:
            continue
        if not any((caps.get(c) or {}).get("status") in USABLE for c in need):
            have = ", ".join(f"{c} {(caps.get(c) or {}).get('status', 'not recorded')}" for c in need)
            rep.error(f"{label}: evidence comes from {ref} ({kind}), but the session could not read it ({have}); "
                      "remove those claims or record the capability truthfully")


def _evidence_paths(data):
    prefixes = [s["location"].rstrip("/") for s in data["sources_used"]
                if s["kind"] in ("local-directory", "github", "source-code")]
    out = {}
    for e in data["evidence"]:
        loc = e["locator"]
        if loc.startswith(("http://", "https://")):
            continue
        path = re.sub(r":\d+(?:-\d+)?$", "", loc.split("#")[0]).strip()
        for p in prefixes:
            if path.startswith(p + "/"):
                out[e["id"]] = path[len(p) + 1:]
    return out


def _check_index(folder, data, rep, label, strict):
    detail = data.get("coverage_detail")
    index_name = (detail or {}).get("index") or "index.json"
    index_path = os.path.join(folder, index_name)
    if not os.path.exists(index_path):
        if detail:
            rep.error(f"{label}: coverage_detail refers to {index_name}, which is missing")
        return
    index = load_json(index_path)
    modules = set(index.get("modules", {}))
    paths = {f["path"] for f in index.get("files", [])}
    analysed = set((detail or {}).get("modules_analysed", []))
    skipped = {s["module"] for s in (detail or {}).get("modules_skipped", [])}
    if not detail:
        _flag(rep, strict, f"{label}: has an index.json but no coverage_detail saying which modules were analysed")
    else:
        for mod in sorted((analysed | skipped) - modules):
            rep.error(f"{label}: coverage_detail names module '{mod}', which is not in the index")
        left = sorted(modules - analysed - skipped)
        if left and data["coverage"] == "complete":
            rep.error(f"{label}: coverage is 'complete' but modules were not analysed: {', '.join(left)}")
        elif left:
            rep.warn(f"{label}: {len(left)} module(s) not analysed yet: {', '.join(left[:8])}"
                     + ("..." if len(left) > 8 else ""))
        for mod in sorted(analysed & modules):
            if not os.path.exists(os.path.join(folder, "summaries", summary_name(mod) + ".md")):
                _flag(rep, strict, f"{label}: analysed module '{mod}' has no summaries/{summary_name(mod)}.md")
    for eid, p in sorted(_evidence_paths(data).items()):
        if paths and p not in paths:
            rep.error(f"{label}: evidence {eid} points at {p}, which is not in the index")
    stale = index.get("stale_features") or []
    if stale:
        rep.error(f"{label}: features whose evidence changed must be re-analysed: {', '.join(stale)}")


def _check_scan(folder, rep, label, strict):
    path = os.path.join(folder, "security-scan.json")
    if not os.path.exists(path):
        return
    scan = load_json(path)
    for err in schema_errors(scan, load_schema("security-scan.schema.json")):
        rep.error(f"{label}: security-scan.json {err}")
    if scan.get("high") and not scan.get("acknowledged"):
        _flag(rep, strict, f"{label}: {scan['high']} high-severity security finding(s) not yet shown to the user "
                           "(set acknowledged: true once they have seen them)")


def check_secrets(mixer_dir):
    """No credential may appear anywhere in mixer/ (documented placeholders such as AKIA...EXAMPLE are allowed)."""
    rep = Report()
    for base, dirs, files in os.walk(mixer_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for name in files:
            if not name.endswith((".md", ".json", ".jsonl", ".csv", ".txt", ".log", ".sql", ".yaml", ".yml", ".xml")):
                continue
            path = os.path.join(base, name)
            with open(path, encoding="utf-8", errors="replace") as f:
                for n, line in enumerate(f, start=1):
                    for kind, _value, placeholder in find_secrets(line):
                        if placeholder:
                            continue
                        rel = os.path.relpath(path, mixer_dir)
                        rep.error(f"secrets: {rel}:{n} contains what looks like a {kind}; remove it "
                                  "(Feature Mixer artifacts must never hold credentials)")
    return rep


def _load_menu_rows(mixer_dir):
    from validate_feature_menu import load_menu
    path = os.path.join(mixer_dir, "feature-menu.csv")
    if not os.path.exists(path):
        return [], []
    header, rows = load_menu(path)
    return header, [r for r in rows if r.get("id")]


def check_design(mixer_dir, kept_ids, strict=False):
    rep = Report()
    design = os.path.join(mixer_dir, "design")
    _sections(os.path.join(design, "prd.md"), PRD_SECTIONS, rep, "design")
    _sections(os.path.join(design, "architecture.md"), ARCH_SECTIONS, rep, "design")
    path = os.path.join(design, "architecture.json")
    if not os.path.exists(path):
        rep.error("design: missing architecture.json")
        return rep
    try:
        arch = load_json(path)
    except ValueError as e:
        rep.error(str(e))
        return rep
    for err in schema_errors(arch, load_schema("architecture.schema.json")):
        rep.error(f"design: architecture.json {err}")
    if rep.errors:
        return rep

    names = [m["name"] for m in arch["modules"]]
    for n in sorted({n for n in names if names.count(n) > 1}):
        rep.error(f"design: module '{n}' is defined twice")
    graph = {m["name"]: m["depends_on"] for m in arch["modules"]}
    for m in arch["modules"]:
        for d in m["depends_on"]:
            if d not in graph:
                rep.error(f"design: module '{m['name']}' depends on unknown module '{d}'")
    for cyc in find_cycles(graph):
        rep.error("design: circular module dependency " + " -> ".join(cyc))
    owner = {}
    for m in arch["modules"]:
        for ent in m.get("owns_entities", []):
            owner.setdefault(ent, []).append(m["name"])
    for ent, mods in sorted(owner.items()):
        if len(mods) > 1:
            _flag(rep, strict, f"design: entity {ent} is owned by several modules ({', '.join(mods)}); give it one owner")

    placed = {}
    for m in arch["modules"]:
        for f in m["features"]:
            placed.setdefault(f, []).append(m["name"])
    for f, mods in sorted(placed.items()):
        if f not in kept_ids:
            rep.error(f"design: module(s) {', '.join(mods)} build {f}, which is not kept")
        if len(mods) > 1:
            rep.warn(f"design: {f} is split across modules {', '.join(mods)}; name one owner")
    for f in sorted(kept_ids):
        if f not in placed:
            rep.error(f"design: kept feature {f} is not assigned to any module")

    in_slice = {}
    for s in arch["slices"]:
        for f in s["features"]:
            in_slice.setdefault(f, []).append(s["id"])
            if f not in kept_ids:
                rep.error(f"design: slice {s['id']} includes {f}, which is not kept")
    for f in sorted(kept_ids):
        if f not in in_slice:
            rep.error(f"design: kept feature {f} is not in any slice of the roadmap")

    seen = set()
    for ep in arch["api"]:
        key = (ep["method"], ep["path"].rstrip("/").lower())
        if key in seen:
            rep.error(f"design: API endpoint {ep['method']} {ep['path']} is defined twice")
        seen.add(key)
        if ep["module"] not in graph:
            rep.error(f"design: API endpoint {ep['method']} {ep['path']} belongs to unknown module '{ep['module']}'")
    routes = [n["route"].rstrip("/").lower() or "/" for n in arch.get("navigation", [])]
    for r in sorted({r for r in routes if routes.count(r) > 1}):
        rep.error(f"design: navigation route {r} is defined twice")
    unapproved = [d["id"] for d in arch["decisions"] if d.get("approved") is False]
    if unapproved:
        rep.warn(f"design: decisions not approved yet: {', '.join(unapproved)}")
    _check_style(arch, graph, rep, strict)
    rep.merge(check_merge_plan(mixer_dir, kept_ids, strict))
    return rep


def _check_style(arch, graph, rep, strict):
    style = arch.get("style")
    if not style:
        _flag(rep, strict, "design: architecture.json has no 'style': record the chosen architecture style, the "
                           "drivers, and the alternatives considered")
        return
    sel = style["selected"]
    alts = [a["style"] for a in style["alternatives"]]
    if len(set(alts) - {sel}) < 2:
        rep.error("design: style.alternatives must compare at least two other architecture styles")
    if sel in alts:
        rep.error(f"design: style.alternatives lists the selected style '{sel}' again")
    services = {m.get("service") for m in arch["modules"] if m.get("service")}
    if sel in ("microservices", "service-oriented"):
        missing = [m["name"] for m in arch["modules"] if not m.get("service")]
        if missing:
            rep.error(f"design: {sel} needs a service for every module; missing: {', '.join(missing)}")
        if len(services) < 2:
            rep.error(f"design: {sel} with fewer than two services is a monolith; choose modular-monolith or split")
    if sel == "event-driven" or arch.get("events"):
        events = arch.get("events") or []
        if sel == "event-driven" and not events:
            rep.error("design: event-driven architecture needs an 'events' list (name, producer, consumers)")
        for ev in events:
            for mod in [ev["producer"]] + ev["consumers"]:
                if mod not in graph:
                    rep.error(f"design: event {ev['name']} names unknown module '{mod}'")
    if sel == "hybrid" and not (services or arch.get("events")):
        rep.error("design: hybrid architecture should say which parts differ (services or events)")
    if sel == "modular-monolith" and len(services) > 1:
        rep.warn("design: modular-monolith but modules name several services; is it really one deployable?")


def check_merge_plan(mixer_dir, kept_ids, strict=False, feature_status=None):
    """mixer/merge-plan.json: the unified features built from kept menu rows."""
    rep = Report()
    path = os.path.join(mixer_dir, "merge-plan.json")
    if not os.path.exists(path):
        _flag(rep, strict, "merge plan: missing merge-plan.json (one unified feature per kept capability)")
        return rep
    try:
        plan = load_json(path)
    except ValueError as e:
        rep.error(str(e))
        return rep
    for err in schema_errors(plan, load_schema("merge-plan.schema.json")):
        rep.error(f"merge plan: {err}")
    if rep.errors:
        return rep
    header, rows = _load_menu_rows(mixer_dir)
    by_id = {r["id"]: r for r in rows}
    ufs = plan["unified_features"]
    uids = [u["id"] for u in ufs]
    for u in sorted({u for u in uids if uids.count(u) > 1}):
        rep.error(f"merge plan: unified feature id {u} is used twice")
    norm = [re.sub(r"[^a-z0-9]+", " ", u["name"].lower()).strip() for u in ufs]
    for n in sorted({n for n in norm if norm.count(n) > 1}):
        rep.error(f"merge plan: two unified features are both called '{n}': duplicate functionality")

    home = {}
    for u in ufs:
        for mid in u["menu_ids"]:
            home.setdefault(mid, []).append(u["id"])
            if mid not in by_id:
                rep.error(f"merge plan: {u['id']} includes {mid}, which is not on the menu")
            elif mid not in kept_ids:
                rep.error(f"merge plan: {u['id']} includes {mid}, which is not kept")
    for mid in sorted(kept_ids):
        if mid not in home:
            rep.error(f"merge plan: kept feature {mid} is not in any unified feature")
        elif len(home[mid]) > 1:
            rep.error(f"merge plan: {mid} appears in {', '.join(home[mid])}; it must be built once")

    groups = {}
    for mid in kept_ids:
        r = by_id.get(mid)
        if r and r.get("merge_group"):
            groups.setdefault(r["merge_group"], []).append(mid)
    for g, mids in sorted(groups.items()):
        mtype = canonical_merge_type(by_id[mids[0]].get("merge_type"))
        homes = {home.get(m, ["?"])[0] for m in mids}
        if mtype in ("identical", "similar", "complementary") and len(homes) > 1:
            rep.error(f"merge plan: group '{g}' is {mtype} but its kept features are split across "
                      f"{', '.join(sorted(homes))}: build them as one unified feature")
        if mtype == "separate" and len(homes) < len(mids):
            rep.error(f"merge plan: group '{g}' is separate, so each kept feature needs its own unified feature")

    unified = set(uids)
    graph = {u["id"]: list(u["depends_on"]) for u in ufs}
    for u in ufs:
        rows_here = [by_id[m] for m in u["menu_ids"] if m in by_id]
        ev = {e for r in rows_here for e in split_ids(r.get("evidence_refs"))}
        sf = {e for r in rows_here for e in split_ids(r.get("source_features"))}
        requested_only = rows_here and all([x.lower() for x in split_ids(r.get("source_app"))] == ["new"]
                                           for r in rows_here)
        if not u["evidence"] and not requested_only:
            rep.error(f"merge plan: {u['id']} has no evidence; only a feature the user requested (all its menu rows "
                      "source_app 'new') may have none")
        extra = sorted(set(u["evidence"]) - ev) if ev else []
        if extra:
            rep.error(f"merge plan: {u['id']} cites evidence {', '.join(extra)} that its menu rows do not")
        for r in rows_here:
            if split_ids(r.get("evidence_refs")) and not set(split_ids(r.get("evidence_refs"))) & set(u["evidence"]):
                rep.warn(f"merge plan: {u['id']} keeps none of {r['id']}'s evidence")
        if "source_features" in header and sf and set(u["source_features"]) - sf:
            rep.error(f"merge plan: {u['id']} lists source features its menu rows do not")
        if len(u["menu_ids"]) > 1 and u["merge_type"] == "unique":
            rep.error(f"merge plan: {u['id']} merges several menu rows but is marked unique")
        for d in u["depends_on"]:
            if d not in unified:
                rep.error(f"merge plan: {u['id']} depends on unknown unified feature {d}")
        for r in rows_here:
            for dep in split_ids(r.get("depends_on")):
                target = home.get(dep, [None])[0]
                if target and target != u["id"] and target not in u["depends_on"]:
                    rep.warn(f"merge plan: {u['id']} should depend on {target} ({r['id']} needs {dep})")
        if u["compatibility"] in ("conflict", "incompatible"):
            _flag(rep, strict, f"merge plan: {u['id']} still has compatibility '{u['compatibility']}'")
        if feature_status is not None:
            states = [feature_status.get(m, "untested") for m in u["menu_ids"]]
            expect = "failed" if "failed" in states else "verified" if all(s == "verified" for s in states) \
                else "unverified" if all(s in ("verified", "unverified") for s in states) else "untested"
            if u["validation"] != expect:
                _flag(rep, strict, f"merge plan: {u['id']} says validation '{u['validation']}' but the verified "
                                   f"test results say '{expect}'")
    for cyc in find_cycles(graph):
        rep.error("merge plan: circular dependency " + " -> ".join(cyc))
    return rep


def slices_status(mixer_dir):
    path = os.path.join(mixer_dir, "design", "architecture.json")
    if not os.path.exists(path):
        return None
    return {s["id"]: s["status"] for s in load_json(path).get("slices", [])}


def check_integration(mixer_dir, kept_ids, strict=None):
    import verify_tests
    rep = Report()
    _sections(os.path.join(mixer_dir, "integration-report.md"), INTEGRATION_SECTIONS, rep, "integration")
    sub, result = verify_tests.verify(mixer_dir, set(kept_ids), strict)
    rep.merge(sub)
    if os.path.exists(os.path.join(mixer_dir, "merge-plan.json")) and not sub.errors:
        rep.merge(check_merge_plan(mixer_dir, set(kept_ids), bool(strict), result["features"]))
    return rep


def kept_from_menu(mixer_dir):
    from validate_feature_menu import load
    path = os.path.join(mixer_dir, "feature-menu.csv")
    if not os.path.exists(path):
        return set()
    return {r["id"] for r in load(path) if r.get("pick", "").lower() == "keep"}


def _workspace(mixer_dir):
    path = os.path.join(mixer_dir, "project.json")
    project = load_json(path) if os.path.exists(path) else {}
    caps_path = os.path.join(mixer_dir, "capabilities.json")
    caps = load_json(caps_path).get("capabilities") if os.path.exists(caps_path) else None
    return workspace_format(project) >= 3, caps


def check_all(mixer_dir):
    rep = Report()
    strict, caps = _workspace(mixer_dir)
    path = os.path.join(mixer_dir, "project.json")
    project = load_json(path) if os.path.exists(path) else {}
    access = {s.get("id"): s.get("access") for s in project.get("sources", [])}
    sources = os.path.join(mixer_dir, "sources")
    if os.path.isdir(sources):
        for name in sorted(os.listdir(sources)):
            if os.path.isdir(os.path.join(sources, name)):
                rep.merge(check_source(os.path.join(sources, name), strict=strict, capabilities=caps,
                                       access=access.get(name.split("-", 1)[0]), fmt=workspace_format(project)))
    kept = kept_from_menu(mixer_dir)
    if os.path.isdir(os.path.join(mixer_dir, "design")):
        rep.merge(check_design(mixer_dir, kept, strict))
    if os.path.exists(os.path.join(mixer_dir, "integration-report.json")):
        rep.merge(check_integration(mixer_dir, kept, strict))
    rep.merge(check_secrets(mixer_dir))
    return rep


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check Feature Mixer artifacts.")
    parser.add_argument("mixer_dir", nargs="?")
    parser.add_argument("--source", help="check one source folder only")
    args = parser.parse_args(argv)
    if not args.mixer_dir and not args.source:
        parser.print_help()
        return 2
    target = args.source or args.mixer_dir
    if not os.path.isdir(target):
        print(f"error: not a folder: {target}")
        return 2
    if args.source:
        mixer = os.path.dirname(os.path.dirname(os.path.abspath(args.source)))
        strict, caps = _workspace(mixer) if os.path.exists(os.path.join(mixer, "project.json")) else (False, None)
        rep = check_source(args.source, strict=strict, capabilities=caps)
    else:
        rep = check_all(args.mixer_dir)
    for line in rep.lines():
        print(line)
    if rep.ok:
        print("artifacts are valid")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
