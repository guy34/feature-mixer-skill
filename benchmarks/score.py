#!/usr/bin/env python3
"""Score a Feature Mixer run against a benchmark scenario's answer key.

    python3 benchmarks/score.py benchmarks/scenarios/1-overlapping/ground-truth.json RUN/mixer [--json]

Measures (each 0 to 1, or "n/a" when the scenario does not test it):
  feature discovery   recall: answer-key features found in the source reports
                      precision: reported features that match an answer-key feature
  fabrication         reported features that match a "should not exist" keyword (count)
  merge accuracy      answer-key groups merged with an accepted merge type, incompatible
                      pairs kept apart, required dependencies present
  compatibility       answer-key conflicts found in compat/compatibility-report.json
  honesty             partial coverage admitted, weakly evidenced features not marked
                      high confidence, known gaps listed as unknowns, capabilities decided
  large repository    index, module coverage record, feature modules analysed, summaries
  integration         (full mode) every kept feature verified by verify_tests.py
  test execution      (full mode) share of reported tests verified against evidence
  validator           validate_project.py exit code at the phase the mode ends on
  missing             answer-key features not found, and kept features not verified

Matching is by keywords in each reported feature's name, description and
subfeatures, per app. It is deliberately simple and is documented in
benchmarks/README.md; read the details in the JSON output before trusting a
number. Standard library only.
"""

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "feature-mixer", "scripts")
sys.path.insert(0, SCRIPTS)

from mixerlib import canonical_merge_type, find_cycles, load_json, split_ids  # noqa: E402

CONF = {"low": 1, "medium": 2, "high": 3}


def text_of(feature):
    parts = [feature.get("name", ""), feature.get("description", "")] + list(feature.get("subfeatures", []))
    return " ".join(parts).lower()


def matches(gt, app, text):
    if gt["app"] != app:
        return False
    if gt.get("any") and not any(k in text for k in gt["any"]):
        return False
    if any(k not in text for k in gt.get("all", [])):
        return False
    return not any(k in text for k in gt.get("none", []))


def load_reports(mixer):
    project = load_json(os.path.join(mixer, "project.json"))
    reports = {}
    for s in project.get("sources", []):
        path = os.path.join(mixer, "sources", f"{s['id']}-{s['slug']}", "source.json")
        if os.path.exists(path):
            reports[s["id"]] = (s, load_json(path))
    return project, reports


def ratio(ok, total):
    return round(ok / total, 3) if total else "n/a"


def score(gt, mixer):
    out = {"scenario": gt["scenario"], "mode": gt["mode"], "details": {}}
    project, reports = load_reports(mixer)
    feats = []
    for app, (_, rep) in reports.items():
        for f in rep.get("features", []):
            feats.append((app, f))

    # discovery
    found = {}
    matched_reported = 0
    fabricated = []
    for app, f in feats:
        t = text_of(f)
        hits = [g["key"] for g in gt["features"] if matches(g, app, t)]
        for k in hits:
            found.setdefault(k, []).append(f["id"])
        if hits:
            matched_reported += 1
        elif any(k in t for k in gt.get("fabrication", [])):
            fabricated.append(f["id"])
    out["feature_recall"] = ratio(len(found), len(gt["features"]))
    out["feature_precision"] = ratio(matched_reported, len(feats))
    out["fabricated"] = len(fabricated)
    out["details"]["found"] = found
    out["details"]["not_found"] = [g["key"] for g in gt["features"] if g["key"] not in found]
    out["details"]["fabricated"] = fabricated
    out["details"]["reported_features"] = len(feats)

    if gt.get("rules"):
        blob = json.dumps([r for _, r in reports.values()]).lower()
        rules_found = [r["name"] for r in gt["rules"] if any(k in blob for k in r["any"])]
        out["rules_found"] = ratio(len(rules_found), len(gt["rules"]))
        out["details"]["rules_found"] = rules_found

    # merge accuracy
    rows = []
    menu = os.path.join(mixer, "feature-menu.csv")
    if os.path.exists(menu):
        from validate_feature_menu import load
        rows = load(menu)
    by_sf = {}
    for r in rows:
        for sf in split_ids(r.get("source_features")):
            by_sf.setdefault(sf, []).append(r)
    rows_for = lambda key: [r for sf in found.get(key, []) for r in by_sf.get(sf, [])]  # noqa: E731
    checks, ok, merge_notes = 0, 0, []
    for g in gt.get("groups", []):
        checks += 1
        member_rows = [rows_for(m) for m in g["members"]]
        if not all(member_rows):
            merge_notes.append(f"group {g['members']}: not every member reached the menu")
            continue
        flat = [r for rs in member_rows for r in rs]
        groups = {r.get("merge_group", "") for r in flat}
        types = {canonical_merge_type(r.get("merge_type")) for r in flat}
        if len(groups) == 1 and "" not in groups and len(types) == 1 and types <= set(g["types"]):
            ok += 1
        else:
            merge_notes.append(f"group {g['members']}: merge_group {sorted(groups)}, merge_type {sorted(types)}, "
                               f"expected one group of type {g['types']}")
    for a, b in gt.get("incompatible_pairs", []):
        checks += 1
        ra, rb = rows_for(a), rows_for(b)
        ids_b = {r["id"] for r in rb}
        linked = any(set(split_ids(r.get("conflicts_with"))) & ids_b for r in ra) or \
            any(set(split_ids(r.get("conflicts_with"))) & {x["id"] for x in ra} for r in rb)
        both_kept = any(r.get("pick") == "keep" for r in ra) and any(r.get("pick") == "keep" for r in rb)
        if ra and rb and linked and not both_kept:
            ok += 1
        else:
            merge_notes.append(f"incompatible {a} / {b}: linked={linked}, both kept={both_kept}")
    if gt.get("dependencies"):
        graph = {r["id"]: split_ids(r.get("depends_on")) for r in rows}

        def reaches(src, dst):
            seen, stack = set(), [src]
            while stack:
                n = stack.pop()
                if n == dst:
                    return True
                if n not in seen:
                    seen.add(n)
                    stack += graph.get(n, [])
            return False
        for a, b in gt["dependencies"]:
            checks += 1
            ra, rb = rows_for(a), rows_for(b)
            if ra and rb and any(reaches(x["id"], y["id"]) for x in ra for y in rb if x["id"] != y["id"]):
                ok += 1
            else:
                merge_notes.append(f"dependency {a} -> {b} not recorded")
    out["merge_accuracy"] = ratio(ok, checks)
    out["details"]["merge"] = merge_notes

    # compatibility
    report_path = os.path.join(mixer, "compat", "compatibility-report.json")
    conflicts = load_json(report_path)["conflicts"] if os.path.exists(report_path) else []
    want = gt.get("conflicts", [])
    hit = [c for c in want if any(x["kind"] == c["kind"] and c["subject"].lower() in x["subject"].lower()
                                  for x in conflicts)]
    out["compatibility_recall"] = ratio(len(hit), len(want))
    out["details"]["conflicts_missed"] = [c for c in want if c not in hit]
    out["details"]["conflicts_reported"] = len(conflicts)

    # honesty
    h_checks, h_ok, h_notes = 0, 0, []
    for app, expected in (gt.get("coverage") or {}).items():
        if expected != "partial":
            continue
        h_checks += 1
        actual = reports.get(app, (None, {}))[1].get("coverage")
        if actual == "partial":
            h_ok += 1
        else:
            h_notes.append(f"{app} coverage {actual}, expected partial")
    for item in gt.get("honesty", []):
        for fid in found.get(item["feature"], []):
            h_checks += 1
            app = fid.split("-")[0]
            f = next(x for x in reports[app][1]["features"] if x["id"] == fid)
            if CONF[f["confidence"]] <= CONF[item["max_confidence"]] and f["basis"] != "observed":
                h_ok += 1
            else:
                h_notes.append(f"{fid} is {f['basis']}/{f['confidence']} ({item['reason']})")
        if item["feature"] not in found:
            h_checks += 1
            unknowns = " ".join(u for _, r in reports.values() for u in r.get("unknowns", [])).lower()
            if any(w in unknowns for w in item["feature"].split("-")[1:]):
                h_ok += 1
            else:
                h_notes.append(f"{item['feature']} neither reported with low confidence nor listed as unknown")
    for word in gt.get("unknowns_mention", []):
        h_checks += 1
        unknowns = " ".join(u for _, r in reports.values() for u in r.get("unknowns", [])).lower()
        if word in unknowns:
            h_ok += 1
        else:
            h_notes.append(f"unknowns do not mention '{word}'")
    caps_path = os.path.join(mixer, "capabilities.json")
    h_checks += 1
    if os.path.exists(caps_path):
        caps = load_json(caps_path)["capabilities"]
        if all(caps.get(c, {}).get("status") not in (None, "not-checked")
               for c in ("browser", "web_fetch", "repository_access", "external_api")):
            h_ok += 1
        else:
            h_notes.append("capabilities left not-checked")
    else:
        h_notes.append("no capabilities.json")
    h_checks += 1
    if fabricated:
        h_notes.append(f"{len(fabricated)} fabricated feature(s)")
    else:
        h_ok += 1
    out["honesty"] = ratio(h_ok, h_checks)
    out["details"]["honesty"] = h_notes

    # large repository
    if gt.get("large"):
        lg = gt["large"]
        src, rep = reports.get(lg["app"], (None, {}))
        folder = os.path.join(mixer, "sources", f"{src['id']}-{src['slug']}") if src else ""
        l_checks, l_ok, l_notes = 4, 0, []
        idx_path = os.path.join(folder, "index.json")
        index = load_json(idx_path) if src and os.path.exists(idx_path) else None
        if index and len(index.get("modules", {})) >= lg["total_modules_min"]:
            l_ok += 1
        else:
            l_notes.append("no index.json with the whole repository")
        detail = rep.get("coverage_detail") or {}
        if detail.get("modules_analysed") is not None:
            l_ok += 1
        else:
            l_notes.append("no coverage_detail")
        analysed = set(detail.get("modules_analysed", []))
        missing = [m for m in lg["feature_modules"] if m not in analysed]
        if not missing:
            l_ok += 1
        else:
            l_notes.append(f"feature modules not analysed: {missing}")
        summ = os.path.join(folder, "summaries")
        if analysed and all(os.path.exists(os.path.join(summ, ("_root" if m == "(root)" else m.replace("/", "__"))
                                                       + ".md")) for m in analysed):
            l_ok += 1
        else:
            l_notes.append("summaries missing for analysed modules")
        out["large_repository"] = ratio(l_ok, l_checks)
        out["details"]["large"] = l_notes
    else:
        out["large_repository"] = "n/a"

    # integration and tests (full mode)
    kept = {r["id"] for r in rows if r.get("pick") == "keep"}
    missing_func = [f"not discovered: {k}" for k in out["details"]["not_found"]]
    if gt["mode"] == "full":
        import verify_tests
        rep, result = verify_tests.verify(mixer, kept)
        verified = [f for f in kept if result["features"].get(f) == "verified"]
        out["integration_completeness"] = ratio(len(verified), len(kept))
        tests = result["tests"]
        out["test_execution"] = ratio(sum(1 for s in tests.values() if s == "passed"), len(tests))
        out["details"]["verify_errors"] = rep.errors[:10]
        missing_func += [f"kept but not verified: {f}" for f in sorted(kept - set(verified))]
    else:
        out["integration_completeness"] = "n/a"
        out["test_execution"] = "n/a"
    out["missing"] = missing_func

    phase = "integration" if gt["mode"] == "full" else "architecture"
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "validate_project.py"), mixer, "--phase", phase],
                       capture_output=True, text=True)
    out["validator_exit"] = r.returncode
    out["details"]["validator_tail"] = r.stdout.strip().splitlines()[-6:]
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score a Feature Mixer run.")
    parser.add_argument("ground_truth")
    parser.add_argument("mixer")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    gt = load_json(args.ground_truth)
    if not os.path.exists(os.path.join(args.mixer, "project.json")):
        print(json.dumps({"scenario": gt["scenario"], "error": "no project.json: the run produced no workspace"}))
        return 1
    result = score(gt, args.mixer)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for k, v in result.items():
            if k != "details":
                print(f"{k:26} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
