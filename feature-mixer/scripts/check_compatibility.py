#!/usr/bin/env python3
"""Compatibility analysis across the source apps, before any integration.

Usage:
    python3 check_compatibility.py MIXER_DIR [--all] [--write] [--json] [--strict]

Reads mixer/project.json, every mixer/sources/<id>-<slug>/source.json, and
optionally:
  mixer/feature-menu.csv            limits the analysis to kept features (unless --all)
  mixer/compat/aliases.json         names Claude decided mean the same thing
                                    {"entities": {"Ticket": "Task"}, "fields": {"full_name": "name"}}
  mixer/compat/manual-conflicts.json  conflicts Claude found by reasoning (same shape as below)
  mixer/compat/resolutions.json     decisions per conflict id {"decision", "approved", "by", "date"}

Checks:
  database     duplicate entities, primary key differences, field type
               mismatches, foreign keys, naming style, migrations needed
  api          duplicate endpoints, contract mismatches, auth differences,
               version conflicts, method conflicts
  application  authentication, session handling, authorization model and
               roles, shared state, route collisions, UI components,
               business rules, shared integrations
  dependency   everything check_dependencies.py reports

--write saves mixer/compat/compatibility-report.json and .md.
Exit codes: 0 no unresolved critical conflict (critical or high with
--strict), 1 otherwise, 2 bad input. Standard library only, no network.
"""

import argparse
import json
import os
import re
import sys

import check_dependencies
from mixerlib import (
    SEVERITIES, apply_resolutions, blocking, guide, load_json, load_resolutions,
    load_sources, make_conflict, split_ids,
)
from validate_feature_menu import load_menu

GUIDE = {
    "duplicate-entity": {
        "solutions": ["Merge into one table holding the fields kept features need",
                      "Keep separate tables if the two only share a name, and rename one"],
        "recommended": "Merge into one entity; list every field's origin in architecture.json",
    },
    "primary-key": {
        "solutions": ["Pick one key type for the merged entity and re-key the other source's rows",
                      "Keep a legacy_id column holding the old key during migration"],
        "recommended": "Use one key type (uuid is usual for merged data) and add a legacy_id column while migrating",
    },
    "field-type": {
        "solutions": ["Choose the wider type and convert the narrower data",
                      "Split into two fields if they mean different things"],
        "recommended": "One type per field; convert in a migration",
    },
    "foreign-key": {
        "solutions": ["Add the missing referenced entity to the extraction",
                      "Align the foreign key type with the referenced primary key"],
        "recommended": "Fix the reference before designing the schema",
    },
    "naming-style": {
        "solutions": ["Pick one naming style for tables and fields and map the others"],
        "recommended": "Use one style (snake_case is usual for SQL)",
    },
    "duplicate-endpoint": {
        "solutions": ["Keep one endpoint and adapt clients of the other",
                      "Keep both under different paths if they serve different needs"],
        "recommended": "One endpoint per job in the unified API",
    },
    "contract": {
        "solutions": ["Define one request and response shape and convert at the edges",
                      "Version the endpoint if existing clients need the old shape"],
        "recommended": "One contract per endpoint, written into the API spec",
    },
    "endpoint-auth": {
        "solutions": ["Put every endpoint behind the one auth system the architecture chooses"],
        "recommended": "Same auth scheme for every endpoint",
    },
    "api-version": {
        "solutions": ["Start the unified API at one version", "Keep a compatibility layer for old clients"],
        "recommended": "One versioning scheme for the unified API",
    },
    "method": {
        "solutions": ["Pick one method convention for updates (PATCH for partial, PUT for full)"],
        "recommended": "One convention, written into the API spec",
    },
    "auth-provider": {
        "solutions": ["Choose one identity provider and migrate accounts to it",
                      "Link accounts by verified email during migration"],
        "recommended": "One identity system for the unified app",
    },
    "auth-methods": {
        "solutions": ["Offer the union of kept sign-in methods through one identity system",
                      "Drop sign-in methods no kept feature needs"],
        "recommended": "One identity system that offers the sign-in methods kept features need",
    },
    "session": {
        "solutions": ["Choose one session mechanism (http-only cookie sessions are the safer default for web apps)",
                      "Use tokens only where a client cannot hold cookies"],
        "recommended": "One session mechanism for the whole app",
    },
    "authorization-model": {
        "solutions": ["Choose one authorization model and express the others' rules in it"],
        "recommended": "One authorization model with one permission check function",
    },
    "roles": {
        "solutions": ["Map every source role to a unified role set and write the mapping down",
                      "Model special powers (such as approving) as permissions, not extra roles"],
        "recommended": "One role set plus explicit permissions; map every source role",
    },
    "state": {
        "solutions": ["Give each feature its own namespaced state", "Merge into one store with one owner"],
        "recommended": "Namespace shared state by module",
    },
    "route": {
        "solutions": ["Merge both screens into one page with sections",
                      "Move one to a different path"],
        "recommended": "One route per screen in the unified navigation",
    },
    "component": {
        "solutions": ["One component with the union of variants the kept screens use"],
        "recommended": "One component in the design system",
    },
    "business-rule": {
        "solutions": ["Choose one value and record why", "Make it a setting if both are legitimate"],
        "recommended": "Pick one value with the user; make it configurable only if both are needed",
    },
    "integration": {
        "solutions": ["Use one connection to the service, shared by every feature that needs it"],
        "recommended": "One integration module per external service",
    },
    "unknown-type": {
        "solutions": ["Read the source's schema or migrations for the type", "Record it as unknown and decide in the architecture"],
        "recommended": "Find the real type before designing the merged entity",
    },
}

SEVERITY = {
    "duplicate-entity": "medium", "primary-key": "critical", "field-type": "high",
    "foreign-key": "high", "naming-style": "low", "duplicate-endpoint": "medium",
    "contract": "high", "endpoint-auth": "high", "api-version": "medium", "method": "low",
    "auth-provider": "high", "auth-methods": "medium", "session": "high",
    "authorization-model": "high", "roles": "high", "state": "medium", "route": "high",
    "component": "low", "business-rule": "high", "integration": "low", "unknown-type": "info",
}

TYPE_SYNONYMS = {
    "integer": ("int", "integer", "bigint", "smallint", "serial", "bigserial", "int4", "int8", "long"),
    "uuid": ("uuid", "guid"),
    "text": ("text", "string", "str", "varchar", "char", "character varying", "citext", "nvarchar", "clob"),
    "binary": ("bytes", "blob", "bytea", "binary", "varbinary", "bytearray", "buffer"),
    "timestamp": ("timestamp", "timestamptz", "datetime", "timestamp with time zone"),
    "date": ("date",),
    "boolean": ("bool", "boolean", "bit"),
    "number": ("float", "double", "real", "decimal", "numeric", "number", "money"),
    "json": ("json", "jsonb", "object"),
    "array": ("array", "list"),
}
_TYPE_LOOKUP = {syn: canon for canon, syns in TYPE_SYNONYMS.items() for syn in syns}


def norm_type(t):
    """'VARCHAR(80)', 'integer primary key autoincrement', 'timestamp with time zone' -> canonical."""
    t = str(t or "").strip().lower()
    t = re.sub(r"\(.*?\)", "", t).strip()
    if t in _TYPE_LOOKUP:
        return _TYPE_LOOKUP[t]
    for n in (3, 2, 1):
        head = " ".join(t.split()[:n])
        if head in _TYPE_LOOKUP:
            return _TYPE_LOOKUP[head]
    return t or "unknown"


def norm_path(path):
    """'/api/v1/Users/:id/' -> ('/api/users/{}', 'v1')"""
    p = str(path).strip().lower().rstrip("/") or "/"
    version = None
    m = re.search(r"/(v\d+)(?=/|$)", p)
    if m:
        version = m.group(1)
        p = p[:m.start()] + p[m.end():]
    p = re.sub(r"\{[^}]*\}|:[a-z0-9_]+|<[^>]*>|\[[^\]]*\]", "{}", p)
    return p or "/", version


def _style(name):
    if "_" in name:
        return "snake_case"
    if re.search(r"[a-z][A-Z]", name):
        return "camelCase"
    return None


class Scope:
    """Which source items take part: all, or only those linked to kept features."""

    def __init__(self, kept_source_features=None, kept_apps=None):
        self.features = kept_source_features
        self.apps = kept_apps

    def app_in(self, app):
        return self.apps is None or app in self.apps

    def item_in(self, app, item):
        if not self.app_in(app):
            return False
        if self.features is None:
            return True
        linked = item.get("features") or []
        return not linked or any(f in self.features for f in linked)


def scope_from_menu(mixer_dir, project):
    path = os.path.join(mixer_dir, "feature-menu.csv")
    if not os.path.exists(path):
        return Scope(), "all extracted items (no feature menu yet)"
    header, rows = load_menu(path)
    kept = [r for r in rows if r.get("id") and r.get("pick", "").lower() == "keep"]
    if not kept:
        return Scope(), "all extracted items (nothing kept yet)"
    from mixerlib import app_ids_for
    apps = {a for r in kept for a in app_ids_for(r.get("source_app"), project)}
    feats = {f for r in kept for f in split_ids(r.get("source_features"))}
    return Scope(feats if "source_features" in header else None, apps), "kept features only"


def menu_ids_by_source_feature(mixer_dir, kept_only=False):
    path = os.path.join(mixer_dir, "feature-menu.csv")
    if not os.path.exists(path):
        return {}
    _, rows = load_menu(path)
    out = {}
    for r in rows:
        if kept_only and r.get("pick", "").lower() != "keep":
            continue
        for f in split_ids(r.get("source_features")):
            out.setdefault(f, set()).add(r["id"])
    return out


DB_KINDS = ("duplicate-entity", "primary-key", "field-type", "foreign-key", "naming-style", "schema", "data",
            "migration")
API_KINDS = ("duplicate-endpoint", "contract", "endpoint-auth", "api-version", "method", "api")
DEP_KINDS = ("version", "runtime", "runtime-mix", "framework", "duplicate-library", "circular-module",
             "vulnerability", "dependency")


def category_of(kind):
    return ("database" if kind in DB_KINDS else "api" if kind in API_KINDS
            else "dependency" if kind in DEP_KINDS else "application")


def _c(kind, subject, apps, detail, features=(), category=None, severity=None):
    sol, rec = guide(GUIDE, kind)
    cat = category or category_of(kind)
    return make_conflict(cat, kind, subject, apps, severity or SEVERITY[kind], detail, sol, rec, features)


RISK_ORDER = {"none": 0, "low": 1, "high": 2}
SAFE_WIDENING = {("integer", "number"), ("integer", "text"), ("number", "text"), ("date", "timestamp"),
                 ("uuid", "text"), ("boolean", "text"), ("json", "text"), ("timestamp", "text"), ("date", "text")}


def type_change_risk(src, dst):
    if dst is None:
        return "high", f"target type not decided (from {src})"
    if src == dst:
        return "none", "same type"
    if (src, dst) in SAFE_WIDENING:
        return "low", f"{src} to {dst} keeps every value"
    return "high", f"{src} to {dst} can lose or reject values"


def _arch_entities(arch):
    """{(app, source entity name lower): architecture entity} from merged_from."""
    out = {}
    for e in (arch or {}).get("entities", []):
        for origin in e.get("merged_from", []):
            if ":" in origin:
                app, name = origin.split(":", 1)
                out[(app, name.lower())] = e
    return out


def analyse(reports, scope=None, aliases=None, arch=None):
    """reports: {app_id: source.json}. Returns (conflicts, migrations).
    arch (architecture.json) is optional: with entity fields it finds data that would be dropped."""
    scope = scope or Scope()
    aliases = aliases or {}
    ent_alias = {k.lower(): v for k, v in (aliases.get("entities") or {}).items()}
    field_alias = {k.lower(): v.lower() for k, v in (aliases.get("fields") or {}).items()}
    conflicts, migrations = [], []
    apps = sorted(a for a in reports if scope.app_in(a))

    def fname(n):
        n = str(n).lower()
        return field_alias.get(n, n)

    def ref_name(value):
        """'User', 'User.id', 'users(id)' -> 'user' (singular, lower-case)."""
        v = re.split(r"[.(]", str(value or ""))[0].strip().lower()
        return v[:-1] if v.endswith("s") and not v.endswith("ss") else v

    # entities in scope, plus every entity they point at (shared data stays in scope)
    in_scope = {}
    for app in apps:
        ents = reports[app].get("entities", [])
        by_ref = {}
        for e in ents:
            by_ref.setdefault(ref_name(e["name"]), e)
        chosen = {e["name"] for e in ents if scope.item_in(app, e)}
        frontier = list(chosen)
        while frontier:
            name = frontier.pop()
            e = next(x for x in ents if x["name"] == name)
            for fk in e.get("foreign_keys", []):
                target = by_ref.get(ref_name(fk.get("references")))
                if target and target["name"] not in chosen:
                    chosen.add(target["name"])
                    frontier.append(target["name"])
        in_scope[app] = chosen

    # ---- database
    entities = {}
    for app in apps:
        own = {}
        for e in reports[app].get("entities", []):
            own.setdefault(ref_name(e["name"]), e)
        for e in reports[app].get("entities", []):
            if e["name"] not in in_scope[app]:
                continue
            canon = ent_alias.get(e["name"].lower(), e["name"])
            entities.setdefault(canon.lower(), {})[app] = e
            for fk in e.get("foreign_keys", []):
                target = ref_name(fk.get("references"))
                if target not in own:
                    conflicts.append(_c("foreign-key", f"{app}.{e['name']}.{fk.get('field')}", [app],
                                        f"{app}: {e['name']}.{fk.get('field')} references {fk.get('references')}, "
                                        f"which is not in {app}'s extracted entities", e.get("features", []),
                                        severity="medium"))
                    continue
                fk_field = next((f for f in e.get("fields", []) if f.get("name") == fk.get("field")), None)
                pk = (own[target].get("primary_key") or {})
                if fk_field and pk and norm_type(fk_field.get("type")) != norm_type(pk.get("type")):
                    conflicts.append(_c("foreign-key", f"{app}.{e['name']}.{fk.get('field')}", [app],
                                        f"{app}: {e['name']}.{fk.get('field')} is {fk_field.get('type')} but "
                                        f"{fk.get('references')}'s key is {pk.get('type')}", e.get("features", [])))

    styles = {}
    for name, per_app in sorted(entities.items()):
        for app, e in per_app.items():
            for f in e.get("fields", []):
                s = _style(f.get("name", ""))
                if s:
                    styles.setdefault(s, set()).add(app)
        if len(per_app) < 2:
            continue
        involved = sorted(per_app)
        feats = [f for e in per_app.values() for f in e.get("features", [])]
        label = next(iter(per_app.values()))["name"]
        names = ", ".join(f"{a}:{per_app[a]['name']}" for a in involved)
        field_sets = {a: {fname(f["name"]): norm_type(f.get("type")) for f in per_app[a].get("fields", [])}
                      for a in involved}
        all_fields = sorted(set().union(*[set(fs) for fs in field_sets.values()]))
        only = [f"{f} (only {', '.join(a for a in involved if f in field_sets[a])})"
                for f in all_fields if sum(f in field_sets[a] for a in involved) < len(involved)]
        detail = f"{label} exists in {names}"
        if only:
            detail += "; fields not shared: " + ", ".join(only)
        conflicts.append(_c("duplicate-entity", name, involved, detail, feats))
        steps = []

        pks = {a: norm_type((per_app[a].get("primary_key") or {}).get("type")) for a in involved}
        unknown_pk = sorted(a for a, t in pks.items() if t == "unknown")
        if unknown_pk:
            conflicts.append(_c("unknown-type", f"{name}.primary-key", involved,
                                f"{label} primary key type is not known for {', '.join(unknown_pk)}; find it "
                                "before deciding the merged key", feats, category="database", severity="info"))
        pks = {a: t for a, t in pks.items() if t != "unknown"}
        if len(set(pks.values())) > 1:
            d = ", ".join(f"{a}: {pks[a]}" for a in involved)
            conflicts.append(_c("primary-key", name, involved, f"{label} primary keys differ ({d})", feats))
            steps.append({"change": f"re-key rows to one primary key type ({d}) and rewrite foreign keys that "
                                    "point at them", "risk": "high",
                          "data_loss": [], "note": "old ids and anything outside that stores them stop matching"})

        for f in all_fields:
            types = {a: field_sets[a][f] for a in involved if f in field_sets[a]}
            unknown = sorted(a for a, t in types.items() if t == "unknown")
            if unknown and len(types) > 1:
                conflicts.append(_c("unknown-type", f"{name}.{f}", list(types),
                                    f"{label}.{f} type is not known for {', '.join(unknown)}", feats,
                                    category="database", severity="info"))
            types = {a: t for a, t in types.items() if t != "unknown"}
            if len(set(types.values())) > 1:
                d = ", ".join(f"{a}: {t}" for a, t in sorted(types.items()))
                conflicts.append(_c("field-type", f"{name}.{f}", list(types), f"{label}.{f} types differ ({d})",
                                    feats))
                steps.append({"change": f"convert {f} to one type ({d})", "risk": "high", "data_loss": [],
                              "note": "decide the target type in the architecture"})
        if only:
            steps.append({"change": "add fields that only some sources have: " + ", ".join(only), "risk": "low",
                          "data_loss": []})
        migrations.append({"id": f"migration:{name}", "entity": label, "apps": involved, "steps": steps})

    # data the unified schema would drop or narrow (needs architecture.json entity fields)
    targets = _arch_entities(arch)
    by_id = {m["id"]: m for m in migrations}
    for app in apps:
        for e in reports[app].get("entities", []):
            if e["name"] not in in_scope[app]:
                continue
            target = targets.get((app, e["name"].lower()))
            if not target or not target.get("fields"):
                continue
            tfields = {fname(f["name"]): norm_type(f.get("type")) for f in target["fields"]}
            for f in target["fields"]:
                for origin in f.get("from", []):
                    if origin.lower().startswith(f"{app.lower()}:"):
                        tfields.setdefault(fname(origin.split(":", 1)[1].split(".")[-1]), norm_type(f.get("type")))
            mid = f"migration:{target['name'].lower()}"
            m = by_id.get(mid)
            if m is None:
                m = {"id": mid, "entity": target["name"], "apps": [], "steps": []}
                by_id[mid] = m
                migrations.append(m)
            if app not in m["apps"]:
                m["apps"] = sorted(set(m["apps"]) | {app})
            dropped = [fl["name"] for fl in e.get("fields", []) if fname(fl["name"]) not in tfields]
            if dropped:
                m["steps"].append({"change": f"{app}.{e['name']} fields not kept in {target['name']}: "
                                             + ", ".join(dropped), "risk": "high", "data_loss": dropped})
            for fl in e.get("fields", []):
                n = fname(fl["name"])
                if n in tfields:
                    risk, why = type_change_risk(norm_type(fl.get("type")), tfields[n])
                    if risk != "none":
                        m["steps"].append({"change": f"{app}.{e['name']}.{fl['name']}: {why}", "risk": risk,
                                           "data_loss": [fl["name"]] if risk == "high" else []})
    for m in migrations:
        if not m["steps"]:
            m["steps"].append({"change": "merge rows from every source into one table", "risk": "low",
                               "data_loss": []})
        m["changes"] = [st["change"] for st in m["steps"]]
        m["risk"] = max((st["risk"] for st in m["steps"]), key=RISK_ORDER.get)
        m["data_loss"] = sorted({x for st in m["steps"] for x in st["data_loss"]})
        m["destructive"] = m["risk"] == "high"

    if len(styles) > 1:
        d = "; ".join(f"{s}: {', '.join(sorted(a))}" for s, a in sorted(styles.items()))
        conflicts.append(_c("naming-style", "fields", [a for v in styles.values() for a in v],
                            f"Field naming styles differ ({d})"))

    # ---- api
    endpoints, paths, versions = {}, {}, {}
    for app in apps:
        for ep in reports[app].get("endpoints", []):
            if not scope.item_in(app, ep):
                continue
            p, ver = norm_path(ep.get("path", ""))
            ver = ep.get("version") or ver
            method = str(ep.get("method", "")).upper()
            endpoints.setdefault((method, p), {})[app] = (ep, ver)
            paths.setdefault(p, {}).setdefault(app, set()).add(method)
            versions.setdefault(app, set()).add(ver or "none")

    for (method, p), per_app in sorted(endpoints.items()):
        if len(per_app) < 2:
            continue
        involved = sorted(per_app)
        feats = [f for ep, _ in per_app.values() for f in ep.get("features", [])]
        subject = f"{method} {p}"
        originals = ", ".join(f"{a}: {per_app[a][0].get('path')}" for a in involved)
        conflicts.append(_c("duplicate-endpoint", subject, involved, f"{subject} exists in {originals}", feats))
        for part in ("request", "response"):
            shapes = {a: {fname(k): norm_type(v) for k, v in (per_app[a][0].get(part) or {}).items()}
                      for a in involved}
            shared = set.intersection(*[set(s) for s in shapes.values()]) if shapes else set()
            bad = [f for f in sorted(shared) if len({shapes[a][f] for a in involved}) > 1]
            if bad:
                d = "; ".join(f"{f}: " + ", ".join(f"{a} {shapes[a][f]}" for a in involved) for f in bad)
                conflicts.append(_c("contract", f"{subject} {part}", involved,
                                    f"{subject} {part} fields disagree ({d})", feats))
        auths = {a: str(per_app[a][0].get("auth", "unknown")).lower() for a in involved}
        if len(set(auths.values())) > 1:
            d = ", ".join(f"{a}: {v}" for a, v in auths.items())
            conflicts.append(_c("endpoint-auth", subject, involved, f"{subject} uses different auth ({d})", feats))
        vers = {a: per_app[a][1] or "none" for a in involved}
        if len(set(vers.values())) > 1:
            d = ", ".join(f"{a}: {v}" for a, v in vers.items())
            conflicts.append(_c("api-version", subject, involved, f"{subject} versions differ ({d})", feats))

    for p, per_app in sorted(paths.items()):
        if len(per_app) < 2:
            continue
        writes = {a: sorted(m & {"PUT", "PATCH"}) for a, m in per_app.items()}
        used = {tuple(v) for v in writes.values() if v}
        if len(used) > 1:
            d = ", ".join(f"{a}: {'/'.join(v)}" for a, v in sorted(writes.items()) if v)
            conflicts.append(_c("method", p, list(per_app), f"Updates to {p} use different methods ({d})"))

    # ---- application
    auths = {a: reports[a].get("auth") or {} for a in apps}
    auths = {a: v for a, v in auths.items() if v}

    def differ(key, kind, label, as_set=False):
        vals = {}
        for a, au in auths.items():
            v = au.get(key)
            if v in (None, "", [], "unknown"):
                continue
            vals[a] = tuple(sorted(str(x).lower() for x in v)) if as_set else str(v).lower()
        if len(set(vals.values())) > 1:
            d = "; ".join(f"{a}: {', '.join(v) if as_set else v}" for a, v in sorted(vals.items()))
            conflicts.append(_c(kind, key, list(vals), f"{label} differ ({d})"))

    differ("provider", "auth-provider", "Identity providers")
    differ("methods", "auth-methods", "Sign-in methods", as_set=True)
    differ("session", "session", "Session mechanisms")
    differ("model", "authorization-model", "Authorization models")
    differ("roles", "roles", "Role sets", as_set=True)

    def collisions(key, field, kind, label, norm=lambda x: x):
        seen = {}
        for app in apps:
            for item in reports[app].get(key, []):
                if scope.item_in(app, item):
                    seen.setdefault(norm(item.get(field, "")), {})[app] = item
        for name, per_app in sorted(seen.items()):
            if len(per_app) > 1:
                yield name, per_app

    for p, per_app in collisions("routes", "path", "route", "Route", lambda x: norm_path(x)[0]):
        d = ", ".join(f"{a}: {item.get('screen', '?')}" for a, item in sorted(per_app.items()))
        conflicts.append(_c("route", p, list(per_app), f"Route {p} is used by {d}"))
    for key, per_app in collisions("state", "key", "state", "State key"):
        conflicts.append(_c("state", key, list(per_app), f"Shared state key '{key}' in {', '.join(sorted(per_app))}"))
    for name, per_app in collisions("components", "name", "component", "Component", lambda x: str(x).lower()):
        variants = {a: tuple(sorted(item.get("variants", []))) for a, item in per_app.items()}
        if len(set(variants.values())) > 1:
            d = "; ".join(f"{a}: {', '.join(v) or 'none'}" for a, v in sorted(variants.items()))
            conflicts.append(_c("component", name, list(per_app), f"{name} variants differ ({d})"))
    for key, per_app in collisions("rules", "key", "business-rule", "Rule"):
        values = {a: json.dumps(item.get("value"), sort_keys=True) for a, item in per_app.items()}
        if len(set(values.values())) > 1:
            d = ", ".join(f"{a}: {v}" for a, v in sorted(values.items()))
            feats = [f for item in per_app.values() for f in item.get("features", [])]
            conflicts.append(_c("business-rule", key, list(per_app), f"Rule {key} differs ({d})", feats))
    for name, per_app in collisions("integrations", "name", "integration", "Integration", lambda x: str(x).lower()):
        conflicts.append(_c("integration", name, list(per_app),
                            f"{name} is used by {', '.join(sorted(per_app))}: share one connection"))

    return conflicts, migrations


def run(mixer_dir, use_all=False):
    project = load_json(os.path.join(mixer_dir, "project.json"))
    reports = load_sources(mixer_dir, project)
    if use_all:
        scope, scope_label = Scope(), "all extracted items"
    else:
        scope, scope_label = scope_from_menu(mixer_dir, project)
    alias_path = os.path.join(mixer_dir, "compat", "aliases.json")
    aliases = load_json(alias_path) if os.path.exists(alias_path) else {}
    arch_path = os.path.join(mixer_dir, "design", "architecture.json")
    arch = load_json(arch_path) if os.path.exists(arch_path) else None
    conflicts, migrations = analyse(reports, scope, aliases, arch)

    dep_stacks = check_dependencies.collect(mixer_dir)
    dep_stacks = {a: s for a, s in dep_stacks.items() if scope.app_in(a)}
    conflicts += check_dependencies.analyse(dep_stacks, check_dependencies.planned_modules(mixer_dir))
    vulns = [v for v in check_dependencies.audits(mixer_dir) if scope.app_in(v["app"])]
    conflicts += check_dependencies.vulnerability_conflicts(vulns)

    manual_path = os.path.join(mixer_dir, "compat", "manual-conflicts.json")
    if os.path.exists(manual_path):
        for m in load_json(manual_path):
            if m.get("severity") not in SEVERITIES:
                raise ValueError(f"{manual_path}: severity for '{m.get('subject')}' must be one of {', '.join(SEVERITIES)}")
            kind = m.get("kind", "manual")
            category = m.get("category") or category_of(kind)
            conflicts.append(make_conflict(
                category, kind, m["subject"], m.get("apps", []),
                m["severity"], m.get("detail", ""), m.get("solutions", []), m.get("recommended", ""),
                m.get("features", [])))

    by_feature = menu_ids_by_source_feature(mixer_dir, kept_only=scope_label == "kept features only")
    for c in conflicts:
        c["menu_features"] = sorted({mid for f in c["features"] for mid in by_feature.get(f, ())})

    resolutions = load_resolutions(mixer_dir)
    for c in conflicts:  # decisions recorded under a manual conflict's earlier id ("application:...") still count
        legacy = f"application:{c['kind']}:{c['subject']}"
        if c["id"] not in resolutions and legacy != c["id"] and legacy in resolutions:
            resolutions[c["id"]] = resolutions[legacy]
    apply_resolutions(conflicts, resolutions)
    ledger = {a.get("target") for a in project.get("approvals", [])
              if a.get("action") == "migration" and a.get("approved") is True}
    for m in migrations:
        res = resolutions.get(m["id"]) or {}
        m["approved"] = res.get("approved") is True or m["id"] in ledger
        m["needs_approval"] = m["destructive"]
    order = {s: i for i, s in enumerate(SEVERITIES)}
    conflicts.sort(key=lambda c: (order[c["severity"]], c["id"]))
    return {
        "scope": scope_label,
        "apps": [s["id"] for s in project.get("sources", []) if scope.app_in(s["id"])],
        "summary": {s: sum(1 for c in conflicts if c["severity"] == s) for s in SEVERITIES},
        "conflicts": conflicts,
        "migrations": migrations,
    }


def unapproved_migrations(report):
    return [m for m in report["migrations"] if m["needs_approval"] and not m["approved"]]


def to_markdown(report):
    lines = ["# Compatibility report", "",
             f"Scope: {report['scope']}. Apps: {', '.join(report['apps'])}.", "",
             "| Severity | Count |", "|---|---|"]
    lines += [f"| {s} | {n} |" for s, n in report["summary"].items() if n]
    lines.append("")
    for c in report["conflicts"]:
        feats = ", ".join(c["menu_features"] or c["features"]) or "not linked to a feature"
        res = c.get("resolution") or {}
        lines += [
            f"## {c['id']}", "",
            f"- **Conflict:** {c['detail']}",
            f"- **Affected applications:** {', '.join(c['apps']) or 'planned modules'}",
            f"- **Affected features:** {feats}",
            f"- **Severity:** {c['severity']}",
            "- **Possible solutions:** " + "; ".join(c["solutions"]),
            f"- **Recommended resolution:** {c['recommended']}",
            f"- **User approval required:** {'yes' if c['needs_approval'] else 'no'}",
            f"- **Status:** {c['status']}" + (f" ({res.get('decision')})" if res.get("decision") else ""),
            "",
        ]
    if report["migrations"]:
        lines += ["## Migrations", "",
                  "Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or "
                  "rejected). Nothing here is ever run without the user's approval.", "",
                  "| Entity | Apps | Steps | Risk | Data that could be lost | Approved |", "|---|---|---|---|---|---|"]
        for m in report["migrations"]:
            steps = "; ".join(f"{st['change']} ({st['risk']})" for st in m["steps"])
            lines.append(f"| {m['entity']} | {', '.join(m['apps'])} | {steps} | {m['risk']} | "
                         f"{', '.join(m['data_loss']) or '-'} | {'yes' if m['approved'] else 'no'} |")
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compatibility analysis across source apps.")
    parser.add_argument("mixer_dir")
    parser.add_argument("--all", action="store_true", help="analyse every extracted item, not only kept features")
    parser.add_argument("--write", action="store_true", help="save compatibility-report.json and .md")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="also block on unresolved high conflicts")
    args = parser.parse_args(argv)
    try:
        report = run(args.mixer_dir, args.all)
    except (OSError, ValueError, KeyError) as e:
        print(f"error: {e}")
        return 2
    stop = blocking(report["conflicts"], args.strict)
    pending_migrations = unapproved_migrations(report)

    if args.write:
        out = os.path.join(args.mixer_dir, "compat")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "compatibility-report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
        with open(os.path.join(out, "compatibility-report.md"), "w", encoding="utf-8") as f:
            f.write(to_markdown(report))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"scope: {report['scope']}; apps: {', '.join(report['apps'])}")
        counts = ", ".join(f"{s} {n}" for s, n in report["summary"].items() if n) or "none"
        print(f"conflicts: {counts}")
        for c in report["conflicts"]:
            print(f"  [{c['severity']}] {c['id']} ({c['status']})")
        if pending_migrations:
            print("destructive migrations awaiting approval: " + ", ".join(m["id"] for m in pending_migrations))
        if stop:
            print(f"{len(stop)} unresolved conflict(s) block integration: " + ", ".join(c["id"] for c in stop))
        if args.write:
            print("wrote compat/compatibility-report.json and compat/compatibility-report.md")
    return 1 if stop else 0


if __name__ == "__main__":
    sys.exit(main())
