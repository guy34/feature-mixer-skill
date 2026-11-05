#!/usr/bin/env python3
"""Score every run in a results tree and summarise repeated runs.

Usage:
    python3 benchmarks/aggregate.py RUNS_DIR [--out RUNS_DIR/summary.json] [--run-holdout] [--md]

RUNS_DIR holds one folder per run, named <label>__<scenario>__r<n> (for example
improved__3-conflicting__r2), each a folder prepared by prepare_run.py with the run's mixer/ inside.
For every run it computes score.py's metrics with the scenario's answer key; then per label and
scenario: the number of runs, the mean, minimum, maximum and standard deviation of each metric, and
reproducibility: how similar repeated runs are (mean pairwise Jaccard similarity of the answer-key
features they found and of the answer-key conflicts they found; 1.0 means every run found the same).
A run that produced no workspace is scored as a failure, never skipped.

--md prints the comparison table used in RESULTS.md. Standard library only.
"""

import argparse
import itertools
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import score  # noqa: E402

KEYS = os.path.join(HERE, "answer-keys")
METRICS = ("overall", "feature_recall", "feature_precision", "feature_f1", "feature_fn_rate", "feature_fp_rate",
           "fabricated", "merge_accuracy", "compatibility_recall", "conflict_precision", "conflict_false_positives",
           "decision_rate", "honesty", "security_violations", "false_success_claims", "holdout_pass_rate",
           "integration_completeness", "test_execution", "regressions", "interventions", "duration_seconds",
           "validator_exit")


def key_for(scenario):
    for p in (os.path.join(KEYS, f"{scenario}.json"), os.path.join(KEYS, "integration", f"{scenario}.json")):
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    raise FileNotFoundError(f"no answer key for {scenario}")


def score_run(folder, scenario, run_holdout=False):
    gt = key_for(scenario)
    mixer = os.path.join(folder, "mixer")
    if not os.path.exists(os.path.join(mixer, "project.json")):
        return {"scenario": scenario, "error": "no workspace", "overall": 0.0, "details": {}}
    out = score.score(gt, mixer)
    if run_holdout:
        score.holdout(gt, mixer, out)
        out["overall"] = score.overall(out)
    return out


def jaccard(a, b):
    a, b = set(a), set(b)
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def summarise(results):
    groups = {}
    for r in results:
        groups.setdefault((r["label"], r["scenario"]), []).append(r)
    out = []
    for (label, scenario), runs in sorted(groups.items()):
        row = {"label": label, "scenario": scenario, "runs": len(runs)}
        for m in METRICS:
            vals = [r[m] for r in runs if isinstance(r.get(m), (int, float)) and not isinstance(r.get(m), bool)]
            if vals:
                row[m] = {"mean": round(statistics.mean(vals), 3), "min": min(vals), "max": max(vals),
                          "stdev": round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0, "n": len(vals)}
        feats = [sorted((r.get("details") or {}).get("found", {})) for r in runs]
        missed = [[json.dumps(c, sort_keys=True) for c in (r.get("details") or {}).get("conflicts_missed", [])]
                  for r in runs]
        if len(runs) > 1:
            row["reproducibility"] = {
                "features_found": round(statistics.mean(jaccard(a, b) for a, b in itertools.combinations(feats, 2)), 3),
                "conflicts_missed": round(statistics.mean(jaccard(a, b) for a, b in itertools.combinations(missed, 2)),
                                          3)}
        out.append(row)
    return out


def table(summary, metrics=("overall", "feature_f1", "compatibility_recall", "honesty", "fabricated",
                            "security_violations", "false_success_claims", "holdout_pass_rate")):
    head = "| Label | Scenario | Runs | " + " | ".join(metrics) + " | Reproducibility |"
    lines = [head, "|" + "---|" * (len(metrics) + 4)]
    for row in summary:
        cells = []
        for m in metrics:
            v = row.get(m)
            if not v:
                cells.append("n/a")
            elif v["n"] > 1:
                cells.append(f"{v['mean']} ({v['min']}–{v['max']})")
            else:
                cells.append(str(v["mean"]))
        rep = row.get("reproducibility")
        cells.append(f"features {rep['features_found']}" if rep else "one run")
        lines.append(f"| {row['label']} | {row['scenario']} | {row['runs']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score and summarise benchmark runs.")
    ap.add_argument("runs_dir")
    ap.add_argument("--out")
    ap.add_argument("--run-holdout", action="store_true", help="run hidden tests on integration runs' code")
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args(argv)
    results = []
    for name in sorted(os.listdir(a.runs_dir)):
        folder = os.path.join(a.runs_dir, name)
        if not os.path.isdir(folder) or name.count("__") != 2:
            continue
        label, scenario, rep = name.split("__")
        r = score_run(folder, scenario, a.run_holdout)
        r.update(label=label, run=rep, folder=name)
        results.append(r)
    summary = summarise(results)
    data = {"runs": results, "summary": summary}
    out = a.out or os.path.join(a.runs_dir, "summary.json")
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(table(summary) if a.md else f"scored {len(results)} run(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
