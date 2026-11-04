"""Shared helpers for the Feature Mixer validation scripts.

Standard library only, Python 3.8+, no network access. The scripts do the
deterministic checks; Claude does the reasoning, the design and the code.
"""

import csv
import json
import os
import re

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)
SCHEMA_DIR = os.path.join(SKILL_DIR, "schemas")

# Allowed values. schemas/feature.schema.json lists the same values; a test
# keeps the two in step.
PICKS = ("keep", "drop", "later", "skip")
PRIORITIES = ("must", "should", "could")
COMPLEXITIES = ("S", "M", "L", "XL")
MERGE_TYPES = ("identical", "similar", "complementary", "unique", "incompatible", "separate")
# Other names accepted in a menu and read as the canonical type (v2.1).
MERGE_SYNONYMS = {"conflicting": "incompatible", "independent": "unique"}
STRATEGIES = ("reuse", "rebuild", "adapt", "combine", "improve", "reject")
COMPATIBILITY = ("compatible", "adaptable", "conflict", "incompatible", "unknown")
CONFIDENCE = ("high", "medium", "low")
BASIS = ("observed", "documented", "inferred", "unknown")
SEVERITIES = ("critical", "high", "medium", "low", "info")

PHASES = (
    "recon",
    "extraction",
    "selection",
    "compatibility",
    "architecture",
    "implementation",
    "integration",
    "deployment",
)
APPROVAL_PHASES = ("selection", "compatibility", "architecture", "deployment")
CHECKPOINT_PHASES = PHASES[:-1]
PHASE_STATUS = ("pending", "in-progress", "done", "failed", "rolled-back")

# Test results (v2.1). v2.0 reports used pass / fail / skip.
TEST_STATUSES = ("passed", "failed", "not-executed", "skipped", "unverified")
LEGACY_TEST_STATUS = {"pass": "passed", "fail": "failed", "skip": "skipped"}
TEST_LEVELS = ("unit", "feature", "interaction", "api", "database", "auth", "authorization", "navigation",
               "form", "error", "dependency", "journey", "regression")

CAPABILITY_STATUS = ("available", "unavailable", "partial", "not-needed", "not-checked")
CAPABILITIES = ("terminal", "filesystem_write", "test_execution", "browser", "web_fetch",
                "repository_access", "external_api")
APPROVAL_ACTIONS = ("run-source-code", "install-dependencies", "run-tests", "network", "destructive",
                    "migration", "deployment", "other")

# Strong secret patterns: used to scan sources and to make sure no secret
# ever lands in a Feature Mixer artifact.
SECRET_PATTERNS = [
    ("aws-access-key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("private-key", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"),
    ("github-token", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    ("slack-token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    ("google-api-key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("stripe-live-key", r"\b[sr]k_live_[0-9A-Za-z]{20,}\b"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]
WEAK_SECRET_PATTERN = (
    "assigned-secret",
    r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)\b"
    r"\s*[:=]\s*['\"]([^'\"\s]{8,})['\"]",
)


def redact(value):
    value = str(value)
    return f"{value[:4]}... ({len(value)} chars, redacted)" if len(value) > 4 else "(redacted)"


def workspace_format(project):
    """2 = a v2.0 workspace (new checks are warnings); 3 = v2.1 (new checks are errors)."""
    return project.get("format", 2) if isinstance(project, dict) else 2


def canonical_merge_type(value):
    v = (value or "").strip().lower()
    return MERGE_SYNONYMS.get(v, v)

# Feature menu columns. v1 menus have only the first ten and still validate.
V1_REQUIRED = ["id", "feature", "depends_on", "conflicts_with", "pick"]
V1_COLUMNS = [
    "id", "feature", "area", "source_app", "priority", "complexity",
    "depends_on", "conflicts_with", "pick", "notes",
]
V2_COLUMNS = [
    "merge_group", "merge_type", "evidence_refs", "compatibility",
    "implementation_strategy", "confidence", "integration_notes",
]
EXTRA_COLUMNS = ["description", "source_features"]
ALL_COLUMNS = V1_COLUMNS + V2_COLUMNS + EXTRA_COLUMNS

APP_ID = re.compile(r"^[A-Z]{1,3}$")
MENU_ID = re.compile(r"^M\d{2,}$")
SOURCE_REF = re.compile(r"^([A-Z]{1,3})-R\d{2,}$")
EVIDENCE_REF = re.compile(r"^([A-Z]{1,3})-E\d{2,}$")
SCREEN_REF = re.compile(r"^([A-Z]{1,3})-S\d{2,}$")
WORKFLOW_REF = re.compile(r"^([A-Z]{1,3})-W\d{2,}$")
FEATURE_REF = re.compile(r"^([A-Z]{1,3})-F\d{2,}$")
GROUP_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")

BASIS_RANK = {"observed": 3, "documented": 3, "inferred": 2, "unknown": 1}


class Report:
    """Collects errors (must fix), warnings (worth a look) and notes."""

    def __init__(self, title=""):
        self.title = title
        self.errors = []
        self.warnings = []
        self.notes = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def note(self, msg):
        self.notes.append(msg)

    def merge(self, other, prefix=""):
        self.errors += [prefix + m for m in other.errors]
        self.warnings += [prefix + m for m in other.warnings]
        self.notes += [prefix + m for m in other.notes]

    @property
    def ok(self):
        return not self.errors

    def lines(self):
        out = []
        if self.errors:
            out.append(f"{len(self.errors)} problem(s):")
            out += ["  - " + m for m in self.errors]
        if self.warnings:
            out.append(f"{len(self.warnings)} warning(s):")
            out += ["  - " + m for m in self.warnings]
        return out


def split_ids(value):
    """'M01; M02,M03' -> ['M01', 'M02', 'M03']"""
    return [v.strip() for v in (value or "").replace(",", ";").split(";") if v.strip()]


def load_csv(path):
    """Return (header, rows). Each row keeps its line number under '__line__'."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = [h.strip() for h in (reader.fieldnames or []) if h is not None]
        rows = []
        for n, raw in enumerate(reader, start=2):
            row = {(k or "").strip(): (v or "").strip() for k, v in raw.items() if k}
            for col in header:
                row.setdefault(col, "")
            row["__line__"] = n
            rows.append(row)
    return header, rows


def write_csv(path, header, rows):
    """Write rows back in the same column order, atomically."""
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    os.replace(tmp, path)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: not valid JSON ({e.msg}, line {e.lineno})")


def load_schema(name):
    return load_json(os.path.join(SCHEMA_DIR, name))


def find_cycles(graph):
    """Return each cycle found in a directed graph, as [a, b, ..., a]."""
    cycles, seen, state, stack = [], set(), {}, []

    def visit(node):
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, ()):
            if nxt not in graph:
                continue
            if state.get(nxt) == 1:
                cyc = stack[stack.index(nxt):]
                i = cyc.index(min(cyc))
                key = tuple(cyc[i:] + cyc[:i])
                if key not in seen:
                    seen.add(key)
                    cycles.append(list(key) + [key[0]])
            elif nxt not in state:
                visit(nxt)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if node not in state:
            visit(node)
    return cycles


# --- a small JSON Schema checker (the subset our schemas use) ---------------

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}


def _type_name(v):
    for name in ("null", "boolean", "integer", "number", "string", "array", "object"):
        if _TYPES[name](v):
            return name
    return type(v).__name__


def schema_errors(instance, schema, root=None, where="$"):
    """Check instance against schema. Supports type, enum, required,
    properties, additionalProperties, items, minItems, uniqueItems,
    minLength, pattern, minimum and local $ref."""
    root = root if root is not None else schema
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"only local $ref is supported, got {ref}")
        target = root
        for part in ref[2:].split("/"):
            target = target[part]
        return schema_errors(instance, target, root, where)

    errs = []
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](instance) for x in types):
            return [f"{where}: expected {' or '.join(types)}, got {_type_name(instance)}"]
    if "enum" in schema and instance not in schema["enum"]:
        allowed = ", ".join(repr(x) for x in schema["enum"])
        errs.append(f"{where}: {instance!r} is not one of {allowed}")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errs.append(f"{where}: must not be empty")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(f"{where}: {instance!r} does not match {schema['pattern']}")
    if _TYPES["number"](instance) and "minimum" in schema and instance < schema["minimum"]:
        errs.append(f"{where}: {instance} is below {schema['minimum']}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errs.append(f"{where}: missing '{key}'")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                errs += schema_errors(value, props[key], root, f"{where}.{key}")
            elif extra is False:
                errs.append(f"{where}: unexpected '{key}'")
            elif isinstance(extra, dict):
                errs += schema_errors(value, extra, root, f"{where}.{key}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errs.append(f"{where}: needs at least {schema['minItems']} item(s)")
        if schema.get("uniqueItems"):
            dumped = [json.dumps(x, sort_keys=True) for x in instance]
            if len(set(dumped)) != len(dumped):
                errs.append(f"{where}: items must be unique")
        if "items" in schema:
            for i, item in enumerate(instance):
                errs += schema_errors(item, schema["items"], root, f"{where}[{i}]")
    return errs


# --- workspace helpers ------------------------------------------------------

def project_root(mixer_dir):
    """The folder that holds mixer/ (paths in project.json are relative to it)."""
    return os.path.dirname(os.path.abspath(mixer_dir))


def source_dir(mixer_dir, source):
    return os.path.join(mixer_dir, "sources", f"{source['id']}-{source['slug']}")


def load_sources(mixer_dir, project):
    """Return {app_id: source.json dict} for every source that has one."""
    out = {}
    for s in project.get("sources", []):
        path = os.path.join(source_dir(mixer_dir, s), "source.json")
        if os.path.exists(path):
            out[s["id"]] = load_json(path)
    return out


def app_ids_for(value, project):
    """Map a source_app cell ('A;B' or 'TaskBoard; Approvals') to app ids."""
    names = {s["name"].lower(): s["id"] for s in project.get("sources", [])}
    ids = {s["id"] for s in project.get("sources", [])}
    out = []
    for part in split_ids(value):
        if part in ids:
            out.append(part)
        elif part.lower() in names:
            out.append(names[part.lower()])
        elif part.lower() not in ("all", "new"):
            out.append(part)
    return out


def guide(kind_table, kind):
    entry = kind_table.get(kind, {})
    return list(entry.get("solutions", [])), entry.get("recommended", "")


def make_conflict(category, kind, subject, apps, severity, detail, solutions,
                  recommended, features=()):
    return {
        "id": f"{category}:{kind}:{subject}",
        "category": category,
        "kind": kind,
        "subject": subject,
        "apps": sorted(set(apps)),
        "features": sorted(set(features)),
        "severity": severity,
        "detail": detail,
        "solutions": list(solutions),
        "recommended": recommended,
        "needs_approval": severity in ("critical", "high"),
    }


def apply_resolutions(conflicts, resolutions):
    """Mark each conflict open, awaiting-approval or resolved."""
    for c in conflicts:
        res = resolutions.get(c["id"])
        if not res or not str(res.get("decision", "")).strip():
            c["status"] = "open"
            c["resolution"] = None
        elif c["needs_approval"] and res.get("approved") is not True:
            c["status"] = "awaiting-approval"
            c["resolution"] = res
        else:
            c["status"] = "resolved"
            c["resolution"] = res
    return conflicts


def blocking(conflicts, strict=False):
    """Conflicts that stop integration: unresolved critical (and high if strict)."""
    levels = ("critical", "high") if strict else ("critical",)
    return [c for c in conflicts if c["severity"] in levels and c.get("status") != "resolved"]


def load_resolutions(mixer_dir):
    path = os.path.join(mixer_dir, "compat", "resolutions.json")
    if not os.path.exists(path):
        return {}
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object keyed by conflict id")
    return data
