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
        "recommended": "Merge only once it is confirmed they mean the same thing; then list every field's origin in "
                       "architecture.json",
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
    "entity-meaning": {
        "solutions": ["Keep them as separate entities with distinct names (for example UserAccount and LedgerAccount)",
                      "Merge them only if the user confirms they describe the same thing"],
        "recommended": "Ask the user; never merge entities because their names match",
    },
    "possible-alias": {
        "solutions": ["Record them as one entity in compat/aliases.json, with the reason",
                      "Record that they are different, so they are never merged"],
        "recommended": "Ask the user whether these are the same thing; never assume either way",
    },
    "alias-unexplained": {
        "solutions": ["Add the reason to compat/aliases.json: {\"entities\": {\"Ticket\": {\"to\": \"Task\", "
                      "\"reason\": \"...\"}}}"],
        "recommended": "Every alias says why the two names mean the same thing",
    },
    "enum": {
        "solutions": ["Define one value set and a mapping from every source value to it",
                      "Keep the field per source if the states really differ"],
        "recommended": "One value set with an explicit mapping; values without a mapping block the migration",
    },
    "nullability": {
        "solutions": ["Keep the field nullable", "Make it required with a default for rows that have no value"],
        "recommended": "Do not make a field required until every source row has a value or a default is agreed",
    },
    "unique-constraint": {
        "solutions": ["Find duplicates across sources before adding the constraint, and decide how to resolve them",
                      "Drop the constraint if the merged data legitimately repeats values"],
        "recommended": "Check the merged data for duplicates first; never drop rows to satisfy a constraint",
    },
    "default-value": {
        "solutions": ["Choose one default and record why"],
        "recommended": "One default, chosen with the user",
    },
    "exposure-default": {
        "solutions": ["Default to private and let owners share explicitly"],
        "recommended": "Private by default; nothing becomes public through a merge",
    },
    "field-meaning": {
        "solutions": ["Keep two fields with distinct names (for example owner_id and created_by)",
                      "Merge them only if the user confirms they mean the same"],
        "recommended": "Ask the user; never merge fields because their names match or an alias says so",
    },
    "units": {
        "solutions": ["Store one unit (for example integer cents in UTC) and convert at import",
                      "Store the unit with the value"],
        "recommended": "One unit per field, converted in the migration and tested",
    },
    "delete-policy": {
        "solutions": ["Choose one delete behaviour for the relation (restrict is the safe default)",
                      "Use soft deletes so nothing is removed implicitly"],
        "recommended": "Pick with the user; cascading deletes can remove data another source expected to keep",
    },
    "deletion-semantics": {
        "solutions": ["Choose soft or hard delete for the merged entity and convert the other source's rows",
                      "Keep deleted rows from the soft-delete source as archived"],
        "recommended": "Soft delete for merged data unless the user decides otherwise",
    },
    "cardinality": {
        "solutions": ["Model the relation as many-to-many (a join table) so neither source loses links",
                      "Keep one-to-many only if the user confirms the extra links can be dropped"],
        "recommended": "Use the more general relation; never drop links silently",
    },
    "relationship": {
        "solutions": ["Keep every relation a kept feature needs in the merged entity"],
        "recommended": "List each relation's origin in architecture.json",
    },
    "identity-linking": {
        "solutions": ["Link a social or SSO login to an existing account only through a verified email",
                      "Keep separate accounts and offer a manual, authenticated link step"],
        "recommended": "Never merge accounts on an unverified email: that is an account-takeover path",
    },
    "role-map": {
        "solutions": ["Map every source role to a unified role in architecture.json auth.role_mapping"],
        "recommended": "No source role left unmapped",
    },
    "privilege-escalation": {
        "solutions": ["Map the role to a role with the same or fewer permissions",
                      "Record the user's explicit approval if the escalation is intended"],
        "recommended": "Never give a source role more power through the merge without the user's approval",
    },
    "role-meaning": {
        "solutions": ["Define the unified role's permissions explicitly and map each source role by permissions"],
        "recommended": "Same role name does not mean same permissions: compare them",
    },
    "tenancy-model": {
        "solutions": ["Choose one tenant boundary (organisation, workspace...) and assign every row to a tenant",
                      "Keep single-tenant data in one default tenant, decided with the user"],
        "recommended": "One tenant model; every tenant-owned row has a tenant key and every query filters by it",
    },
    "tenant-isolation": {
        "solutions": ["Add the tenant key to the entity and filter every query and API by it",
                      "Mark the entity as shared (global) if the user decides it is not tenant data"],
        "recommended": "No tenant-owned entity without a tenant key; test cross-tenant access is refused",
    },
    "shared-resource": {
        "solutions": ["Decide which tenants can see the shared resource and enforce it",
                      "Make the resource per-tenant"],
        "recommended": "Ask the user how shared resources cross tenant boundaries",
    },
    "idempotency": {
        "solutions": ["Store processed event ids and ignore repeats", "Make each state change conditional on the "
                      "current state, inside one transaction"],
        "recommended": "Every webhook and retry is idempotent; test duplicate delivery and retry after partial "
                       "success",
    },
    "payment-flow": {
        "solutions": ["One billing module owns charges, refunds and their states; the others call it"],
        "recommended": "One source of truth for money movement",
    },
    "storage-provider": {
        "solutions": ["Choose one storage provider and migrate objects with their ids and access rules"],
        "recommended": "One storage service; object ids and permissions carried over and tested",
    },
    "pagination": {
        "solutions": ["Choose one pagination style for the unified API and adapt the others at the edge"],
        "recommended": "One pagination convention, written into the API spec",
    },
    "error-format": {
        "solutions": ["Choose one error format (for example RFC 9457 problem+json) and map the others"],
        "recommended": "One error format, written into the API spec",
    },
    "rate-limit": {
        "solutions": ["Set limits per endpoint in the unified API"],
        "recommended": "Write the limits into the API spec",
    },
    "endpoint-origin": {
        "solutions": ["Point the endpoint's origin at a real source endpoint", "Mark it as new (no origin)"],
        "recommended": "No endpoint claims to come from a source that does not have it",
    },
}

SEVERITY = {
    "duplicate-entity": "medium", "primary-key": "critical", "field-type": "high",
    "foreign-key": "high", "naming-style": "low", "duplicate-endpoint": "medium",
    "contract": "high", "endpoint-auth": "high", "api-version": "medium", "method": "low",
    "auth-provider": "high", "auth-methods": "medium", "session": "high",
    "authorization-model": "high", "roles": "high", "state": "medium", "route": "high",
    "component": "low", "business-rule": "high", "integration": "low", "unknown-type": "info",
    "entity-meaning": "high", "possible-alias": "medium", "alias-unexplained": "low", "enum": "high",
    "nullability": "medium", "unique-constraint": "high", "default-value": "low", "exposure-default": "high",
    "field-meaning": "high", "units": "high", "delete-policy": "high", "deletion-semantics": "medium",
    "cardinality": "high", "relationship": "medium", "identity-linking": "high", "role-map": "high",
    "privilege-escalation": "critical", "role-meaning": "high", "tenancy-model": "high", "tenant-isolation": "critical",
    "shared-resource": "medium", "idempotency": "high", "payment-flow": "high", "storage-provider": "medium",
    "pagination": "medium", "error-format": "medium", "rate-limit": "low", "endpoint-origin": "high",
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


def singular(v):
    if v.endswith("ies") and len(v) > 4:
        return v[:-3] + "y"
    if v.endswith(("sses", "uses", "xes", "zes", "ches", "shes")):
        return v[:-2]
    if v.endswith("s") and not v.endswith(("ss", "us", "is")):
        return v[:-1]
    return v


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
            "migration", "entity-meaning", "possible-alias", "alias-unexplained", "enum", "nullability",
            "unique-constraint", "default-value", "exposure-default", "field-meaning", "units", "delete-policy",
            "deletion-semantics", "cardinality", "relationship", "tenant-isolation")
API_KINDS = ("duplicate-endpoint", "contract", "endpoint-auth", "api-version", "method", "api", "pagination",
             "error-format", "rate-limit", "endpoint-origin")
DEP_KINDS = ("version", "version-uncertain", "runtime", "runtime-mix", "framework", "duplicate-library",
             "circular-module", "vulnerability", "dependency")


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


GENERIC_FIELDS = {"id", "created_at", "updated_at", "createdat", "updatedat", "created", "updated", "name", "uuid"}
SYNONYMS = [
    {"user", "account", "member", "person", "profile", "customer", "client", "participant", "employee"},
    {"organization", "organisation", "org", "company", "tenant", "workspace", "team"},
    {"project", "board", "space"},
    {"task", "ticket", "issue", "todo", "card", "job"},
    {"comment", "note", "reply", "remark"},
    {"document", "file", "attachment", "asset", "upload"},
    {"order", "purchase", "checkout"},
    {"payment", "charge", "transaction"},
    {"invoice", "bill"},
    {"product", "item", "sku", "article"},
    {"tag", "label", "category"},
    {"message", "notification", "alert"},
]
UNIT_KEYS = ("unit", "currency", "timezone", "time_zone", "format", "precision", "scale", "epoch")
TENANT_KEYS = ("tenant_id", "org_id", "organization_id", "organisation_id", "workspace_id", "account_id", "team_id",
               "company_id")
PASSWORD_METHODS = {"password", "email", "email-password", "email/password", "credentials", "local", "username"}
FEDERATED_METHODS = {"oauth", "oauth2", "google", "github", "microsoft", "apple", "sso", "saml", "oidc",
                     "openid", "facebook", "gitlab", "okta", "auth0"}
PRIVILEGED = re.compile(r"(?i)^(?:admin|administrator|owner|superuser|super[-_ ]?admin|root|sysadmin)$")
PAYMENT_NAMES = {"stripe", "paypal", "braintree", "adyen", "square", "razorpay", "paddle", "mollie", "checkout.com"}
STORAGE_NAMES = {"s3", "aws s3", "gcs", "google cloud storage", "azure blob", "azure-blob", "cloudinary", "minio",
                 "local disk", "local-disk", "r2", "backblaze", "dropbox"}


def _words(text):
    return {w for w in re.findall(r"[a-z]{3,}", str(text).lower())} - {"the", "and", "for", "that", "with", "this",
                                                                        "are", "who", "which", "from", "has"}


def _differs(a, b):
    """Two descriptions that share too few words to be the same idea."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / min(len(wa), len(wb)) < 0.34


def _nullable(f):
    if "nullable" in f:
        return bool(f["nullable"])
    if "required" in f:
        return not bool(f["required"])
    return None


def _finalise(m):
    if not m["steps"]:
        m["steps"].append({"change": "merge rows from every source into one table", "risk": "low", "data_loss": []})
    m["changes"] = [st["change"] for st in m["steps"]]
    m["risk"] = max((st["risk"] for st in m["steps"]), key=RISK_ORDER.get)
    m["data_loss"] = sorted({x for st in m["steps"] for x in st["data_loss"]})
    m["destructive"] = m["risk"] == "high"


def _relations(ents, ent_alias, ref_name):
    """{(entity, target): kind} for one app: foreign keys are many-to-one; a table made only of two or more
    foreign keys links its targets many-to-many; explicit "relations" override."""
    canon = lambda n: ent_alias.get(str(n).lower(), n).lower()  # noqa: E731
    by_ref = {ref_name(e["name"]): e["name"] for e in ents}
    out = {}
    for e in ents:
        fks = [fk for fk in e.get("foreign_keys", []) if ref_name(fk.get("references")) in by_ref]
        own = {fl.get("name") for fl in e.get("fields", [])}
        fk_fields = {fk.get("field") for fk in fks}
        targets = [canon(by_ref[ref_name(fk.get("references"))]) for fk in fks]
        if len(fks) >= 2 and own - fk_fields <= GENERIC_FIELDS | {None}:
            for i, a in enumerate(targets):
                for b in targets[i + 1:]:
                    out[(a, b)] = out[(b, a)] = "many-to-many"
        else:
            for t in targets:
                out.setdefault((canon(e["name"]), t), "many-to-one")
        for r in e.get("relations", []) or []:
            if r.get("to") and r.get("kind"):
                out[(canon(e["name"]), canon(r["to"]))] = str(r["kind"]).lower()
    return out


def semantic_checks(reports, apps, in_scope, entities, ent_alias, fname, ref_name, conflicts, migrations_by_id):
    """Meaning, constraints, units, deletes and relations of entities that several sources share, plus entities
    with different names that may be the same thing. Nothing here merges anything: it asks."""
    for name, per_app in sorted(entities.items()):
        if len(per_app) < 2:
            continue
        involved = sorted(per_app)
        label = next(iter(per_app.values()))["name"]
        feats = [f for e in per_app.values() for f in e.get("features", [])]
        mig = migrations_by_id.get(f"migration:{name}")

        def step(change, risk, loss=()):
            if mig is not None:
                mig["steps"].append({"change": change, "risk": risk, "data_loss": list(loss)})

        # does the shared name mean the same thing?
        descs = {a: (per_app[a].get("description") or per_app[a].get("meaning") or "").strip() for a in involved}
        fsets = {a: {fname(f["name"]) for f in per_app[a].get("fields", [])} - GENERIC_FIELDS for a in involved}
        reasons = []
        pairs = [(x, y) for i, x in enumerate(involved) for y in involved[i + 1:]]
        for x, y in pairs:
            if descs[x] and descs[y] and _differs(descs[x], descs[y]):
                reasons.append(f"{x} describes it as '{descs[x][:80]}', {y} as '{descs[y][:80]}'")
            if len(fsets[x]) >= 2 and len(fsets[y]) >= 2:
                j = len(fsets[x] & fsets[y]) / len(fsets[x] | fsets[y])
                if j < 0.2:
                    reasons.append(f"{x} and {y} share {len(fsets[x] & fsets[y])} of "
                                   f"{len(fsets[x] | fsets[y])} non-generic fields")
        if reasons:
            conflicts.append(_c("entity-meaning", name, involved, f"{label} may not mean the same thing in "
                                f"{', '.join(involved)}: " + "; ".join(reasons), feats))

        objs = {a: {fname(f["name"]): f for f in per_app[a].get("fields", [])} for a in involved}
        shared = sorted(set.intersection(*[set(o) for o in objs.values()]))
        for f in shared:
            fo = {a: objs[a][f] for a in involved}
            enums = {a: tuple(sorted(map(str, o.get("enum") or o.get("values") or []))) for a, o in fo.items()
                     if o.get("enum") or o.get("values")}
            if len(set(enums.values())) > 1:
                allv = set().union(*map(set, enums.values()))
                only = "; ".join(f"{a} only: {', '.join(sorted(set(v) - set().union(*[set(w) for b, w in enums.items() if b != a])) or '-')}"
                                 for a, v in sorted(enums.items()))
                conflicts.append(_c("enum", f"{name}.{f}", list(enums), f"{label}.{f} allows different values "
                                    f"({only}; {len(allv)} values in all)", feats))
                step(f"map every value of {f} to one value set ({only})", "high")
            nul = {a: _nullable(o) for a, o in fo.items() if _nullable(o) is not None}
            if len(set(nul.values())) > 1:
                d = ", ".join(f"{a}: {'optional' if v else 'required'}" for a, v in sorted(nul.items()))
                conflicts.append(_c("nullability", f"{name}.{f}", list(nul), f"{label}.{f} is {d}", feats))
                step(f"{f}: rows from {', '.join(a for a, v in sorted(nul.items()) if v)} may have no value; "
                     "making it required rejects them unless a default is agreed", "high")
            uniq = {a: bool(o["unique"]) for a, o in fo.items() if "unique" in o}
            if len(uniq) > 1 and len(set(uniq.values())) > 1:
                d = ", ".join(f"{a}: {'unique' if v else 'not unique'}" for a, v in sorted(uniq.items()))
                conflicts.append(_c("unique-constraint", f"{name}.{f}", list(uniq), f"{label}.{f} is {d}; merged "
                                    "rows can repeat values", feats))
                step(f"{f}: find duplicate values across sources before adding the unique constraint", "high")
            defaults = {a: json.dumps(o.get("default"), sort_keys=True) for a, o in fo.items() if "default" in o}
            if len(defaults) > 1 and len(set(defaults.values())) > 1:
                d = ", ".join(f"{a}: {v}" for a, v in sorted(defaults.items()))
                public = re.search(r"(?i)public|visib|shared|is_public|published", f) and any(
                    re.search(r'(?i)^(true|"public"|"shared"|"anyone"|1)$', v) for v in defaults.values())
                conflicts.append(_c("exposure-default" if public else "default-value", f"{name}.{f}", list(defaults),
                                    f"{label}.{f} defaults differ ({d})" + ("; one source makes new items visible "
                                                                             "to others by default" if public else ""),
                                    feats))
            meanings = {a: (o.get("description") or o.get("meaning") or "").strip() for a, o in fo.items()}
            meanings = {a: v for a, v in meanings.items() if v}
            if len(meanings) > 1 and any(_differs(meanings[x], meanings[y]) for x in meanings for y in meanings
                                         if x < y):
                d = "; ".join(f"{a}: '{v[:60]}'" for a, v in sorted(meanings.items()))
                originals = ", ".join(f"{a}:{fo[a]['name']}" for a in sorted(meanings))
                conflicts.append(_c("field-meaning", f"{name}.{f}", list(meanings),
                                    f"{label}.{f} ({originals}) means different things ({d})", feats))
            for key in UNIT_KEYS:
                units = {a: str(o[key]).lower() for a, o in fo.items() if o.get(key) not in (None, "")}
                if len(units) > 1 and len(set(units.values())) > 1:
                    d = ", ".join(f"{a}: {v}" for a, v in sorted(units.items()))
                    conflicts.append(_c("units", f"{name}.{f}.{key}", list(units), f"{label}.{f} {key} differs ({d})",
                                        feats))
                    step(f"convert {f} to one {key} ({d}) and test the conversion", "high")

        # deletes: per relation and per entity
        pol = {}
        for a in involved:
            for fk in per_app[a].get("foreign_keys", []):
                if fk.get("on_delete"):
                    pol.setdefault(fname(fk.get("field")), {})[a] = str(fk["on_delete"]).lower()
        for field, by in sorted(pol.items()):
            if len(by) > 1 and len(set(by.values())) > 1:
                d = ", ".join(f"{a}: {v}" for a, v in sorted(by.items()))
                conflicts.append(_c("delete-policy", f"{name}.{field}", list(by),
                                    f"deleting what {label}.{field} points at does different things ({d})", feats))
        soft = {}
        for a in involved:
            e = per_app[a]
            mode = e.get("deletion")
            if not mode:
                names = {fl.get("name", "").lower() for fl in e.get("fields", [])}
                mode = "soft" if names & {"deleted_at", "is_deleted", "deleted", "archived_at", "removed_at"} else None
            if mode:
                soft[a] = str(mode).lower()
        if soft and (len(set(soft.values())) > 1 or len(soft) < len(involved)):
            d = ", ".join(f"{a}: {soft.get(a, 'hard delete (no marker found)')}" for a in involved)
            conflicts.append(_c("deletion-semantics", name, involved, f"deleting a {label} means different things "
                                f"({d})", feats))
            step("decide soft or hard delete; rows marked deleted in one source must not reappear or vanish", "high")

    # relations between merged entities: one-to-many in one source, many-to-many in another
    rels = {a: _relations([e for e in reports[a].get("entities", []) if e["name"] in in_scope[a]], ent_alias,
                          ref_name) for a in apps}
    seen = set()
    for a in apps:
        for (x, y), kind in rels[a].items():
            key = tuple(sorted((x, y)))
            if key in seen:
                continue
            kinds = {}
            for b in apps:
                k = rels[b].get((x, y)) or rels[b].get((y, x))
                if k:
                    kinds[b] = k
            if len(set(kinds.values())) > 1:
                seen.add(key)
                d = ", ".join(f"{b}: {k}" for b, k in sorted(kinds.items()))
                conflicts.append(_c("cardinality", f"{key[0]}-{key[1]}", list(kinds),
                                    f"{key[0]} and {key[1]} are related differently ({d})"))
                m = migrations_by_id.get(f"migration:{x}") or migrations_by_id.get(f"migration:{y}")
                if m is not None:
                    m["steps"].append({"change": f"relation {key[0]}-{key[1]}: keep every link ({d})", "risk": "high",
                                       "data_loss": []})

    # different names, possibly the same thing: ask, never assume
    names = {}
    for a in apps:
        for e in reports[a].get("entities", []):
            if e["name"] in in_scope[a]:
                canon = ent_alias.get(e["name"].lower(), e["name"]).lower()
                names.setdefault(canon, {})[a] = e
    keys = sorted(names)
    for i, x in enumerate(keys):
        for y in keys[i + 1:]:
            ax, ay = set(names[x]), set(names[y])
            if not (ax - ay or ay - ax) or (ax == ay and len(ax) == 1):
                continue
            if ax == ay:
                continue
            group = any(singular(x) in g and singular(y) in g for g in SYNONYMS)
            fx = {fname(f["name"]) for e in names[x].values() for f in e.get("fields", [])} - GENERIC_FIELDS
            fy = {fname(f["name"]) for e in names[y].values() for f in e.get("fields", [])} - GENERIC_FIELDS
            overlap = len(fx & fy) >= 3 and len(fx & fy) / max(1, len(fx | fy)) >= 0.6
            if group or overlap:
                why = "the names are often used for the same thing" if group else \
                    f"they share {len(fx & fy)} of {len(fx | fy)} non-generic fields"
                ex = ", ".join(f"{b}:{names[x][b]['name']}" for b in sorted(names[x]))
                ey = ", ".join(f"{b}:{names[y][b]['name']}" for b in sorted(names[y]))
                conflicts.append(_c("possible-alias", f"{x}~{y}", sorted(ax | ay),
                                    f"{ex} and {ey} may be the same thing ({why}); record the decision in "
                                    "compat/aliases.json either way"))

    for m in migrations_by_id.values():
        _finalise(m)


def application_checks(reports, apps, scope, arch, conflicts):
    """Identity, roles, tenancy, payments, storage and API conventions across the sources."""
    auths = {a: reports[a].get("auth") or {} for a in apps}
    methods = {a: {str(m).lower() for m in (au.get("methods") or [])} for a, au in auths.items()}
    pw = sorted(a for a, ms in methods.items() if ms & PASSWORD_METHODS)
    fed = sorted(a for a, ms in methods.items() if ms & FEDERATED_METHODS)
    if pw and fed and set(pw) | set(fed) and len(set(pw) | set(fed)) > 1:
        conflicts.append(_c("identity-linking", "accounts", sorted(set(pw) | set(fed)),
                            f"password sign-in ({', '.join(pw)}) and federated sign-in ({', '.join(fed)}) will meet in "
                            "one account table: the same person can arrive twice, or an attacker can claim an account "
                            "through an unverified email"))
    perms = {}
    for a, au in auths.items():
        for role, ps in (au.get("role_permissions") or {}).items():
            perms.setdefault(str(role).lower(), {})[a] = tuple(sorted(map(str, ps)))
    for role, by in sorted(perms.items()):
        if len(by) > 1 and len(set(by.values())) > 1:
            d = "; ".join(f"{a}: {', '.join(v) or 'none'}" for a, v in sorted(by.items()))
            conflicts.append(_c("role-meaning", role, list(by), f"role '{role}' has different permissions ({d})"))
    roles = {a: [str(r) for r in (au.get("roles") or [])] for a, au in auths.items() if au.get("roles")}
    mapping = ((arch or {}).get("auth") or {}).get("role_mapping")
    if roles and isinstance(mapping, dict):
        flat = {str(k).lower(): str(v) for k, v in mapping.items()}
        for a, rs in sorted(roles.items()):
            for r in rs:
                target = flat.get(f"{a.lower()}:{r.lower()}") or flat.get(r.lower())
                if target is None:
                    conflicts.append(_c("role-map", f"{a}:{r}", [a], f"source role {a}:{r} is not in "
                                        "architecture.json auth.role_mapping"))
                elif PRIVILEGED.match(target) and not PRIVILEGED.match(r):
                    conflicts.append(_c("privilege-escalation", f"{a}:{r}->{target}", [a],
                                        f"{a}:{r} is mapped to {target}, which looks more powerful"))

    ten = {a: reports[a].get("tenancy") or {} for a in apps}
    models = {a: str(t.get("model") or "none").lower() for a, t in ten.items() if t}
    if len(set(models.values())) > 1:
        d = ", ".join(f"{a}: {m}" for a, m in sorted(models.items()))
        conflicts.append(_c("tenancy-model", "tenancy", list(models), f"tenant boundaries differ ({d})"))
    if any(m != "none" for m in models.values()):
        keys = {str(t.get("key")).lower() for t in ten.values() if t.get("key")} | set(TENANT_KEYS)
        roots = {singular(m) for m in models.values() if m != "none"} | \
            {"organization", "organisation", "org", "tenant", "workspace", "team", "company"}
        for e in (arch or {}).get("entities", []):
            fields = {str(f.get("name", "")).lower() for f in e.get("fields", [])}
            if singular(str(e.get("name", "")).lower()) in roots:
                continue  # the tenant itself
            if e.get("shared") or e.get("global") or e.get("tenant_key") or fields & keys:
                continue
            if not e.get("fields"):
                continue
            conflicts.append(_c("tenant-isolation", e["name"], sorted(models),
                                f"{e['name']} has no tenant key in the unified design, so its queries cannot be "
                                "limited to one tenant"))
        for a in apps:
            for e in reports[a].get("entities", []):
                if e.get("shared") and scope.item_in(a, e):
                    conflicts.append(_c("shared-resource", f"{a}:{e['name']}", [a],
                                        f"{a}:{e['name']} is shared across tenants: decide who may see it"))
    for a in apps:
        for i in reports[a].get("integrations", []):
            if not scope.item_in(a, i):
                continue
            if i.get("webhooks") and str(i.get("idempotency") or "none").lower() in ("none", "no", "false", ""):
                conflicts.append(_c("idempotency", f"{a}:{i.get('name')}", [a],
                                    f"{a}'s {i.get('name')} webhooks have no recorded idempotency: a repeated "
                                    "delivery can apply twice"))
    pay = {a: sorted({str(i.get("name")).lower() for i in reports[a].get("integrations", [])
                      if str(i.get("kind", "")).lower() in ("payments", "billing") or
                      str(i.get("name", "")).lower() in PAYMENT_NAMES}) for a in apps}
    pay = {a: v for a, v in pay.items() if v}
    if len(pay) > 1:
        d = ", ".join(f"{a}: {', '.join(v)}" for a, v in sorted(pay.items()))
        conflicts.append(_c("payment-flow", "payments", list(pay), f"several sources move money ({d})"))
    store = {}
    for a in apps:
        for i in reports[a].get("integrations", []):
            n = str(i.get("provider") or i.get("name") or "").lower()
            if str(i.get("kind", "")).lower() == "storage" or n in STORAGE_NAMES:
                store.setdefault(a, set()).add(n)
    if len({frozenset(v) for v in store.values()}) > 1:
        d = ", ".join(f"{a}: {', '.join(sorted(v))}" for a, v in sorted(store.items()))
        conflicts.append(_c("storage-provider", "files", list(store), f"files live in different places ({d})"))
    for key, kind in (("pagination", "pagination"), ("error_format", "error-format"), ("rate_limit", "rate-limit")):
        vals = {}
        for a in apps:
            v = (reports[a].get("api") or {}).get(key)
            eps = {str(ep.get(key)).lower() for ep in reports[a].get("endpoints", []) if ep.get(key)}
            if v:
                eps.add(str(v).lower())
            if eps:
                vals[a] = tuple(sorted(eps))
        if vals and key == "rate_limit":  # an API with no recorded limit differs from one that has a limit
            for a in apps:
                if reports[a].get("endpoints") and a not in vals:
                    vals[a] = ("none recorded",)
        if len(set(vals.values())) > 1:
            d = ", ".join(f"{a}: {', '.join(v)}" for a, v in sorted(vals.items()))
            conflicts.append(_c(kind, key, list(vals), f"API {key.replace('_', ' ')} differs ({d})"))
    known = {}
    for a in apps:
        for ep in reports[a].get("endpoints", []):
            known.setdefault(a, set()).add((str(ep.get("method", "")).upper(), norm_path(ep.get("path", ""))[0]))
    for ep in (arch or {}).get("api", []) or []:
        for origin in ep.get("from", []) or []:
            m = re.match(r"^([A-Z]{1,3}):\s*([A-Za-z]+)\s+(\S+)$", str(origin))
            if not m:
                continue
            a, meth, path = m.groups()
            if (meth.upper(), norm_path(path)[0]) not in known.get(a, set()):
                conflicts.append(_c("endpoint-origin", f"{ep.get('method')} {ep.get('path')}", [a],
                                    f"the unified {ep.get('method')} {ep.get('path')} says it comes from {origin}, "
                                    f"which is not in {a}'s extracted endpoints"))


def analyse(reports, scope=None, aliases=None, arch=None):
    """reports: {app_id: source.json}. Returns (conflicts, migrations).
    arch (architecture.json) is optional: with entity fields it finds data that would be dropped."""
    scope = scope or Scope()
    aliases = aliases or {}
    conflicts, migrations = [], []
    ent_alias, field_alias = {}, {}
    for table, out in (("entities", ent_alias), ("fields", field_alias)):
        for k, v in (aliases.get(table) or {}).items():
            target, reason = (v.get("to"), v.get("reason")) if isinstance(v, dict) else (v, None)
            if not target:
                continue
            out[k.lower()] = target if table == "entities" else str(target).lower()
            if not str(reason or "").strip():
                conflicts.append(_c("alias-unexplained", f"{table}:{k}->{target}", [],
                                    f"compat/aliases.json says {k} means {target} but gives no reason"))
    apps = sorted(a for a in reports if scope.app_in(a))

    def fname(n):
        n = str(n).lower()
        return field_alias.get(n, n)

    def ref_name(value):
        """'User', 'User.id', 'users(id)', 'statuses' -> 'user', 'status' (singular, lower-case)."""
        return singular(re.split(r"[.(]", str(value or ""))[0].strip().lower())

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
        _finalise(m)

    semantic_checks(reports, apps, in_scope, entities, ent_alias, fname, ref_name, conflicts, by_id)
    application_checks(reports, apps, scope, arch, conflicts)

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
