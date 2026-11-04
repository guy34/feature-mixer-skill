#!/usr/bin/env python3
"""Validate a Feature Mixer feature menu, show it, or change picks.

Usage:
    python3 validate_feature_menu.py MENU.csv
    python3 validate_feature_menu.py MENU.csv --show [--format md] [--only keep|drop|later|skip|undecided]
    python3 validate_feature_menu.py MENU.csv --set keep M01,M04,group:notifications
    python3 validate_feature_menu.py MENU.csv --allow-no-keep      (before picks are made)

Checks: duplicate ids, invalid picks, unknown references, missing and
transitive dependencies, circular dependencies, conflicts between kept
features, skip rules, and for v2 menus: merge groups and merge types,
implementation strategies, compatibility, confidence and evidence.

Works with v1 menus (the ten original columns) and v2 menus.
Exit codes: 0 valid, 1 something to fix, 2 unreadable file or bad arguments.
Standard library only, no network.
"""

import argparse
import csv
import sys
from collections import deque

from mixerlib import (
    COMPATIBILITY, COMPLEXITIES, CONFIDENCE, EVIDENCE_REF, FEATURE_REF, GROUP_NAME,
    MENU_ID, MERGE_SYNONYMS, MERGE_TYPES, PICKS, PRIORITIES, STRATEGIES, V1_REQUIRED, V2_COLUMNS,
    Report, canonical_merge_type, find_cycles, load_csv, split_ids, write_csv,
)


def load_menu(path):
    """Return (header, rows) including rows without an id; raise ValueError on missing columns."""
    header, rows = load_csv(path)
    missing = [c for c in V1_REQUIRED if c not in header]
    if missing:
        raise ValueError("missing columns: " + ", ".join(missing))
    return header, rows


def load(path):
    """v1 API: rows that have an id."""
    _, rows = load_menu(path)
    return [r for r in rows if r.get("id")]


def is_v2(header):
    return any(c in header for c in V2_COLUMNS)


def _pick(row):
    return row.get("pick", "").strip().lower()


def _label(row):
    return f"{row['id']} ({row.get('feature', '')})"


def _dep_paths(start, by_id):
    """Breadth-first walk of depends_on; yields (node, path from start)."""
    seen = {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        for dep in split_ids(by_id[node].get("depends_on")):
            if dep in by_id and dep not in seen:
                seen.add(dep)
                yield dep, path + [dep]
                queue.append((dep, path + [dep]))


def validate(rows, header=None):
    """Validate menu rows. Returns a Report; errors must be fixed."""
    if header is None:
        header = [k for k in (rows[0].keys() if rows else []) if not k.startswith("__")]
    v2 = is_v2(header)
    rep = Report()

    real = []
    for r in rows:
        if r.get("id"):
            real.append(r)
        elif any(v for k, v in r.items() if not k.startswith("__")):
            rep.warn(f"line {r.get('__line__', '?')}: row has no id and was ignored")

    by_id = {}
    for r in real:
        if r["id"] in by_id:
            first = by_id[r["id"]].get("__line__", "?")
            rep.error(f"duplicate id {r['id']} on lines {first} and {r.get('__line__', '?')}")
        else:
            by_id[r["id"]] = r

    # values
    for r in by_id.values():
        if not MENU_ID.match(r["id"]):
            rep.warn(f"{_label(r)}: ids are usually M01, M02...")
        p = _pick(r)
        if p and p not in PICKS:
            rep.error(f"{_label(r)}: pick '{r['pick']}' is not one of keep, drop, later, skip (leave it empty while undecided)")
        if r.get("priority") and r["priority"].lower() not in PRIORITIES:
            rep.warn(f"{_label(r)}: priority '{r['priority']}' is not must, should or could")
        if r.get("complexity") and r["complexity"].upper() not in COMPLEXITIES:
            rep.warn(f"{_label(r)}: complexity '{r['complexity']}' is not S, M, L or XL")

    kept = {fid for fid, r in by_id.items() if _pick(r) == "keep"}

    # references
    for r in by_id.values():
        for ref in split_ids(r.get("depends_on")) + split_ids(r.get("conflicts_with")):
            if ref not in by_id:
                rep.error(f"{r['id']} ({r['feature']}): refers to unknown id {ref}")

    # circular dependencies
    graph = {fid: [d for d in split_ids(r.get("depends_on")) if d in by_id] for fid, r in by_id.items()}
    for cyc in find_cycles(graph):
        rep.error("circular dependency: " + " -> ".join(cyc))

    # missing dependencies, direct then transitive
    for fid in sorted(kept):
        r = by_id[fid]
        direct = split_ids(r.get("depends_on"))
        for dep in direct:
            if dep in by_id and dep not in kept:
                d = by_id[dep]
                msg = f"{fid} ({r['feature']}) needs {dep} ({d['feature']}), which is '{d['pick'] or 'unpicked'}'"
                if _pick(d) == "skip":
                    msg += f": skipped features cannot be built, so drop {fid} or provide it another way"
                rep.error(msg)
        for dep, path in _dep_paths(fid, by_id):
            if len(path) < 3 or dep in kept or dep in direct:
                continue
            if all(step in kept for step in path[1:-1]):
                continue  # a kept step in between already reports it
            d = by_id[dep]
            rep.error(
                f"{fid} ({r['feature']}) also needs {dep} ({d['feature']}) through "
                f"{' -> '.join(path)}, which is '{d['pick'] or 'unpicked'}'"
            )

    # conflicts between kept features (once per pair)
    seen_pairs = set()
    for fid in sorted(kept):
        r = by_id[fid]
        for other in split_ids(r.get("conflicts_with")):
            pair = tuple(sorted((fid, other)))
            if other in kept and pair not in seen_pairs:
                seen_pairs.add(pair)
                rep.error(f"{fid} ({r['feature']}) conflicts with {other} ({by_id[other]['feature']}): keep one")

    if v2:
        _validate_v2(by_id, kept, rep)
    return rep


def _validate_v2(by_id, kept, rep):
    groups = {}
    for fid, r in by_id.items():
        label = _label(r)
        mtype = canonical_merge_type(r.get("merge_type"))
        strat = r.get("implementation_strategy", "").lower()
        compat = r.get("compatibility", "").lower()
        conf = r.get("confidence", "").lower()
        group = r.get("merge_group", "")
        is_kept = fid in kept

        if mtype and mtype not in MERGE_TYPES:
            names = ", ".join(MERGE_TYPES + tuple(MERGE_SYNONYMS))
            rep.error(f"{label}: merge_type '{r['merge_type']}' is not one of {names}")
        if strat and strat not in STRATEGIES:
            rep.error(f"{label}: implementation_strategy '{r['implementation_strategy']}' is not one of {', '.join(STRATEGIES)}")
        if compat and compat not in COMPATIBILITY:
            rep.error(f"{label}: compatibility '{r['compatibility']}' is not one of {', '.join(COMPATIBILITY)}")
        if conf and conf not in CONFIDENCE:
            rep.error(f"{label}: confidence '{r['confidence']}' is not high, medium or low")

        if group:
            if not GROUP_NAME.match(group):
                rep.error(f"{label}: merge_group '{group}' should be lower-case words joined by '-'")
            groups.setdefault(group, []).append(fid)
            if not mtype:
                rep.error(f"{label}: is in merge group '{group}' but has no merge_type")
        elif mtype in ("identical", "similar", "complementary", "separate"):
            rep.error(f"{label}: merge_type '{mtype}' needs a merge_group naming the features it relates to")

        if is_kept and strat == "improve" and not r.get("integration_notes", "").strip():
            rep.error(f"{label}: strategy improve needs integration_notes saying what is improved before integration")
        if is_kept and mtype == "separate":
            if strat == "combine":
                rep.error(f"{label}: is separate (deliberately kept apart), so its strategy cannot be combine")
            if not r.get("integration_notes", "").strip():
                rep.error(f"{label}: is separate but integration_notes does not say where its boundary is")

        if mtype == "incompatible" and not split_ids(r.get("conflicts_with")):
            rep.error(f"{label}: is incompatible but conflicts_with does not say what with")

        refs = split_ids(r.get("evidence_refs"))
        for ref in refs:
            if not EVIDENCE_REF.match(ref):
                rep.error(f"{label}: evidence ref '{ref}' should look like A-E01")
        for ref in split_ids(r.get("source_features")):
            if not FEATURE_REF.match(ref):
                rep.error(f"{label}: source feature '{ref}' should look like A-F01")

        if _pick(r) == "skip" and strat not in ("", "reject"):
            rep.error(f"{label}: is skip (cannot be rebuilt) so its strategy must be reject, not '{strat}'")

        if is_kept:
            if not refs:
                rep.error(f"{label}: is kept but has no evidence_refs (every kept feature needs evidence)")
            if strat == "reject":
                rep.error(f"{label}: is kept but its implementation_strategy is reject")
            if not strat:
                rep.warn(f"{label}: is kept but has no implementation_strategy yet")
            if compat == "incompatible" or mtype == "incompatible":
                if strat not in ("rebuild", "adapt"):
                    rep.error(f"{label}: is incompatible as it stands, so keeping it needs strategy rebuild or adapt")
            if compat == "conflict":
                rep.warn(f"{label}: has a compatibility conflict; resolve it in the compatibility report before building")
            if compat in ("", "unknown"):
                rep.warn(f"{label}: compatibility not assessed yet")
            if conf == "low":
                rep.warn(f"{label}: is kept on low-confidence evidence; verify it before building")

    for group, members in sorted(groups.items()):
        types = sorted({canonical_merge_type(by_id[m].get("merge_type")) for m in members
                        if by_id[m].get("merge_type")})
        if len(types) > 1:
            rep.error(f"merge group '{group}' mixes merge types {', '.join(types)}: one group, one type")
            continue
        mtype = types[0] if types else ""
        kept_here = [m for m in members if m in kept]
        names = ", ".join(kept_here)
        if mtype == "unique" and len(members) > 1:
            rep.error(f"merge group '{group}' is unique but has {len(members)} features: {', '.join(members)}")
        if mtype in ("identical", "similar", "complementary", "separate") and len(members) == 1:
            rep.warn(f"merge group '{group}' has only one feature; is it really {mtype}?")
        if mtype == "identical" and len(kept_here) > 1:
            rep.error(f"merge group '{group}' is identical but keeps {names}: keep one and drop the duplicates")
        if mtype == "similar" and len(kept_here) > 1:
            not_combined = [m for m in kept_here if by_id[m].get("implementation_strategy", "").lower() != "combine"]
            if not_combined:
                rep.error(
                    f"merge group '{group}' is similar but keeps {names}: choose one alternative, "
                    f"or set implementation_strategy to combine on every kept row"
                )
        if mtype == "complementary" and len(kept_here) > 1:
            loose = [m for m in kept_here if by_id[m].get("implementation_strategy", "").lower() != "combine"]
            if loose:
                rep.warn(
                    f"merge group '{group}' is complementary: {', '.join(loose)} could be combined into one "
                    f"module with the others (strategy combine)"
                )
        if mtype == "incompatible" and len(kept_here) > 1:
            rep.error(f"merge group '{group}' holds incompatible features but keeps {names}: keep one")


def check(rows):
    """v1 API: (kept ids, list of problem strings)."""
    rep = validate(rows)
    kept = {r["id"] for r in rows if r.get("id") and _pick(r) == "keep"}
    return kept, rep.errors


# --- selection helpers ------------------------------------------------------

def apply_picks(rows, pick, targets):
    """Set pick on ids or group:<name> targets. Returns (changed ids, warnings).
    Raises ValueError for unknown targets or a keep on a skip row."""
    pick = pick.lower()
    if pick not in PICKS + ("undecided",):
        raise ValueError(f"pick must be one of keep, drop, later, skip, undecided (got '{pick}')")
    value = "" if pick == "undecided" else pick
    by_id = {r["id"]: r for r in rows if r.get("id")}
    chosen = []
    for t in split_ids(targets):
        if t.startswith("group:"):
            name = t[len("group:"):]
            members = [r["id"] for r in rows if r.get("id") and r.get("merge_group") == name]
            if not members:
                raise ValueError(f"no merge group called '{name}'")
            chosen += members
        elif t in by_id:
            chosen.append(t)
        else:
            raise ValueError(f"unknown feature id '{t}'")
    warnings = []
    for fid in chosen:
        r = by_id[fid]
        if value == "keep" and _pick(r) == "skip":
            raise ValueError(f"{_label(r)} is skip: it cannot be rebuilt, so it cannot be kept")
        if value in ("drop", "skip") and r.get("priority", "").lower() == "must":
            warnings.append(f"{_label(r)} is a must-have and is now '{value}'")
    for fid in chosen:
        by_id[fid]["pick"] = value
    return list(dict.fromkeys(chosen)), warnings


SHOW_COLUMNS = [
    ("id", "ID"), ("pick", "Pick"), ("feature", "Feature"), ("source_app", "Source"),
    ("description", "Description"), ("priority", "Priority"), ("complexity", "Size"),
    ("depends_on", "Needs"), ("conflicts_with", "Conflicts"), ("merge_type", "Merge type"),
    ("compatibility", "Compatibility"), ("evidence_refs", "Evidence"),
    ("implementation_strategy", "Strategy"),
]


def render(rows, header, fmt="text", only=None):
    """The selection view: rows grouped by merge group."""
    rows = [r for r in rows if r.get("id")]
    if only:
        want = "" if only == "undecided" else only
        rows = [r for r in rows if _pick(r) == want]
    cols = [(k, t) for k, t in SHOW_COLUMNS if k in header]
    groups = {}
    for r in rows:
        groups.setdefault(r.get("merge_group", "") or "", []).append(r)
    out = []
    for g in sorted(groups, key=lambda x: (x == "", x)):
        members = groups[g]
        mtype = members[0].get("merge_type", "")
        title = f"{g} ({mtype})" if g else "not grouped"
        if fmt == "md":
            out.append(f"### {title}\n")
            out.append("| " + " | ".join(t for _, t in cols) + " |")
            out.append("|" + "---|" * len(cols))
            for r in members:
                cells = [(r.get(k, "") or ("undecided" if k == "pick" else "")).replace("|", "/") for k, _ in cols]
                out.append("| " + " | ".join(cells) + " |")
            out.append("")
        else:
            out.append(f"[{title}]")
            for r in members:
                out.append(
                    f"  {r['id']:<5} {(r.get('pick') or 'undecided'):<9} {r.get('feature', '')[:34]:<34} "
                    f"{r.get('source_app', '')[:10]:<10} {r.get('priority', ''):<6} {r.get('complexity', ''):<3} "
                    f"{r.get('implementation_strategy', ''):<8} needs={r.get('depends_on', '') or '-'}"
                )
    return "\n".join(out)


def summary_line(rows):
    rows = [r for r in rows if r.get("id")]
    counts = {}
    for r in rows:
        key = _pick(r) or "unpicked"
        counts[key] = counts.get(key, 0) + 1
    detail = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    return f"{len(rows)} features: {detail}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a Feature Mixer feature menu.")
    parser.add_argument("menu")
    parser.add_argument("--show", action="store_true", help="print the selection view")
    parser.add_argument("--format", choices=("text", "md"), default="text")
    parser.add_argument("--only", choices=PICKS + ("undecided",))
    parser.add_argument("--set", nargs=2, metavar=("PICK", "IDS"),
                        help="set PICK on comma-separated ids or group:<name>, then validate")
    parser.add_argument("--allow-no-keep", action="store_true",
                        help="do not fail when nothing is kept yet (before selection)")
    args = parser.parse_args(argv)

    try:
        header, rows = load_menu(args.menu)
    except (OSError, ValueError, csv.Error) as e:
        print(f"error: {e}")
        return 2

    if args.set:
        try:
            changed, warnings = apply_picks(rows, args.set[0], args.set[1])
        except ValueError as e:
            print(f"error: {e}")
            return 2
        write_csv(args.menu, header, rows)
        print(f"set {args.set[0]} on {', '.join(changed)}")
        for w in warnings:
            print(f"  note: {w}")

    if args.show:
        print(render(rows, header, args.format, args.only))
        print()

    rep = validate(rows, header)
    print(summary_line(rows))
    kept = [r for r in rows if r.get("id") and _pick(r) == "keep"]
    if not kept and not args.allow_no_keep:
        print("nothing is marked keep yet")
        for line in rep.lines():
            print(line)
        return 1
    for line in rep.lines():
        print(line)
    if rep.errors:
        return 1
    print("picks are consistent: every dependency is kept, no conflicts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
