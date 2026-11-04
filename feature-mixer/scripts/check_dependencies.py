#!/usr/bin/env python3
"""Compare the technology stacks of the source apps.

Usage:
    python3 check_dependencies.py MIXER_DIR [--json] [--strict]
    python3 check_dependencies.py --scan A=path/to/app --scan B=path/to/other [--json]

For each source app it reads:
  - package.json and requirements.txt found in the app's local folder
    (project.json sources with a local path, up to three levels deep), and
  - "packages" and "runtimes" recorded in its source.json (for sources that
    have no manifest, such as a website or an API spec).
It also reads the planned module graph from mixer/compat/dependencies.json
("modules") and mixer/design/architecture.json ("modules"), if present.

Reports: package version conflicts, runtime version conflicts, mixed
runtimes, competing frameworks in the same layer, duplicated libraries that
do the same job, and circular module dependencies.

Version checks use the major version of each spec (a heuristic: ^18.2 and
18.x agree, 17 and 18 do not, >=16 accepts 18). Unreadable specs are skipped.

Dependency intelligence (v2.1):
  vulnerabilities  read from audit tool output only: npm audit --json,
                   pip-audit -f json, or osv-scanner --format json, saved as
                   mixer/compat/audit/<APP>-<tool>.json (or --audit APP=FILE).
                   These are "confirmed" (a tool reported them). The scripts
                   never go online; the user approves running the audit tool.
  warnings         unpinned or non-registry specs ("*", latest, git, file:):
                   "unverified", because nothing offline can check them.
  necessity        with an index.json per source (index_repo.py): packages
                   declared but never imported (possibly unused), imported but
                   not declared, and only used by files of dropped features.
                   Import scanning is approximate, so these are suggestions.

Exit codes: 0 no unresolved critical conflict (critical or high with
--strict), 1 otherwise, 2 bad input. Standard library only, no network.
"""

import argparse
import json
import os
import re
import sys

from mixerlib import (
    apply_resolutions, blocking, find_cycles, guide, load_json, load_resolutions,
    load_sources, make_conflict, project_root,
)

FRAMEWORK_LAYERS = {
    "frontend framework": {
        "react": "React", "vue": "Vue", "svelte": "Svelte", "@angular/core": "Angular",
        "solid-js": "Solid", "preact": "Preact",
    },
    "full-stack framework": {
        "next": "Next.js", "nuxt": "Nuxt", "@remix-run/react": "Remix",
        "@sveltejs/kit": "SvelteKit", "astro": "Astro",
    },
    "backend framework": {
        "express": "Express", "fastify": "Fastify", "koa": "Koa", "@nestjs/core": "NestJS",
        "hono": "Hono", "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
    },
    "data layer": {
        "prisma": "Prisma", "@prisma/client": "Prisma", "typeorm": "TypeORM",
        "sequelize": "Sequelize", "drizzle-orm": "Drizzle", "mongoose": "Mongoose",
        "sqlalchemy": "SQLAlchemy", "knex": "Knex",
    },
}
FRAMEWORK_PACKAGES = {pkg for layer in FRAMEWORK_LAYERS.values() for pkg in layer}

DUPLICATE_GROUPS = {
    "HTTP client": ["axios", "node-fetch", "got", "ky", "superagent", "requests", "httpx", "aiohttp"],
    "date library": ["moment", "dayjs", "date-fns", "luxon"],
    "state management": ["redux", "@reduxjs/toolkit", "zustand", "mobx", "jotai", "recoil", "pinia", "vuex"],
    "styling": ["tailwindcss", "styled-components", "@emotion/react", "sass", "bootstrap"],
    "test runner": ["jest", "vitest", "mocha", "pytest"],
    "validation": ["zod", "yup", "joi", "pydantic", "marshmallow"],
    "UI component kit": ["@mui/material", "antd", "@chakra-ui/react", "@mantine/core"],
}

GUIDE = {
    "version": {
        "solutions": [
            "Standardise on the newer major version and update the code that used the older one",
            "Keep the older version only if a kept feature cannot move yet, and isolate it",
        ],
        "recommended": "Use one version, normally the newer major, in the unified app",
    },
    "runtime": {
        "solutions": ["Target one runtime version that every kept feature can run on",
                      "Upgrade the source code that needs the older runtime"],
        "recommended": "Pick the newest runtime version the kept features support",
    },
    "runtime-mix": {
        "solutions": ["Choose one backend runtime and rebuild the features from the other",
                      "Keep two services only if a kept feature truly needs the other runtime"],
        "recommended": "One backend runtime for the unified app, chosen in the architecture phase",
    },
    "framework": {
        "solutions": ["Choose one framework for this layer and rebuild the others' features in it",
                      "Run them side by side only as a short, planned migration"],
        "recommended": "One framework per layer; prefer the one most kept features already use",
    },
    "duplicate-library": {
        "solutions": ["Keep one library for this job and replace calls to the others"],
        "recommended": "Keep one library per job",
    },
    "circular-module": {
        "solutions": ["Move the shared part into its own module both can depend on",
                      "Invert one dependency with an event or callback"],
        "recommended": "Break the cycle before implementation starts",
    },
}

SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "dist", "build", "__pycache__", ".next"}
REQ_LINE = re.compile(r"^([A-Za-z0-9_.\-\[\]]+)\s*(.*)$")
VERSION = re.compile(r"(\d+)")


# --- reading manifests ------------------------------------------------------

def scan_manifests(path, max_depth=3):
    """Read package.json and requirements.txt files under path."""
    packages, runtimes, files = {}, {}, []
    base_depth = path.rstrip(os.sep).count(os.sep)
    for root, dirs, names in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        if root.count(os.sep) - base_depth >= max_depth:
            dirs[:] = []
        if "package.json" in names:
            p = os.path.join(root, "package.json")
            try:
                data = load_json(p)
            except ValueError:
                continue
            files.append(p)
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                for name, spec in (data.get(key) or {}).items():
                    packages.setdefault(name, str(spec))
            node = (data.get("engines") or {}).get("node")
            if node:
                runtimes.setdefault("node", str(node))
        if "requirements.txt" in names:
            p = os.path.join(root, "requirements.txt")
            files.append(p)
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.split("#", 1)[0].strip()
                    if not line or line.startswith("-"):
                        continue
                    m = REQ_LINE.match(line)
                    if m:
                        name = re.sub(r"\[.*\]", "", m.group(1)).lower()
                        packages.setdefault(name, m.group(2).strip() or "*")
        for marker in ("runtime.txt", ".python-version"):
            if marker in names:
                with open(os.path.join(root, marker), encoding="utf-8") as f:
                    text = f.read().strip().replace("python-", "")
                if text:
                    runtimes.setdefault("python", text)
    # a manifest says which runtime the code needs even when no version is pinned
    if any(os.path.basename(f) == "package.json" for f in files):
        runtimes.setdefault("node", "*")
    if any(os.path.basename(f) == "requirements.txt" for f in files):
        runtimes.setdefault("python", "*")
    return {"packages": packages, "runtimes": runtimes, "files": files}


def collect(mixer_dir):
    """Per-app stacks from project.json sources and their source.json."""
    project = load_json(os.path.join(mixer_dir, "project.json"))
    reports = load_sources(mixer_dir, project)
    root = project_root(mixer_dir)
    stacks = {}
    for s in project.get("sources", []):
        stack = {"packages": {}, "runtimes": {}, "files": []}
        rep = reports.get(s["id"], {})
        stack["packages"].update(rep.get("packages") or {})
        stack["runtimes"].update(rep.get("runtimes") or {})
        loc = s.get("local_path")
        if loc:
            path = loc if os.path.isabs(loc) else os.path.join(root, loc)
            if os.path.isdir(path):
                scanned = scan_manifests(path)
                for key in ("packages", "runtimes"):
                    for name, spec in scanned[key].items():
                        stack[key].setdefault(name, spec)
                stack["files"] = [os.path.relpath(f, root) for f in scanned["files"]]
        stacks[s["id"]] = stack
    return stacks


def planned_modules(mixer_dir):
    graph = {}
    for rel in (("compat", "dependencies.json"), ("design", "architecture.json")):
        path = os.path.join(mixer_dir, *rel)
        if not os.path.exists(path):
            continue
        data = load_json(path).get("modules")
        if isinstance(data, dict):
            for name, deps in data.items():
                graph.setdefault(name, list(deps))
        elif isinstance(data, list):
            for m in data:
                graph.setdefault(m.get("name", ""), list(m.get("depends_on", [])))
    return graph


# --- analysis ---------------------------------------------------------------

def parse_spec(spec):
    """Return (major, open_ended) or None when the spec cannot be read."""
    s = str(spec).strip().lower()
    if not s or s in ("*", "x", "latest") or s.startswith(("git", "http", "file:", "link:", "workspace:", "npm:")):
        return None
    m = VERSION.search(s)
    if not m:
        return None
    open_ended = s.startswith(">") and "<" not in s
    return int(m.group(1)), open_ended


def versions_conflict(a, b):
    pa, pb = parse_spec(a), parse_spec(b)
    if pa is None or pb is None:
        return None
    (ma, oa), (mb, ob) = pa, pb
    if oa and ob:
        return False
    if oa:
        return mb < ma
    if ob:
        return ma < mb
    return ma != mb


def _version_conflicts(stacks, key, kind, out):
    names = sorted({n for st in stacks.values() for n in st[key]})
    for name in names:
        users = {app: st[key][name] for app, st in stacks.items() if name in st[key]}
        if len(users) < 2:
            continue
        apps = sorted(users)
        clash = [(a, b) for i, a in enumerate(apps) for b in apps[i + 1:]
                 if versions_conflict(users[a], users[b])]
        if not clash:
            continue
        detail = ", ".join(f"{a} uses {users[a]}" for a in apps)
        if kind == "runtime":
            severity = "high"
        else:
            severity = "high" if name in FRAMEWORK_PACKAGES else "medium"
        sol, rec = guide(GUIDE, kind)
        out.append(make_conflict("dependency", kind, name, apps, severity,
                                 f"{name}: {detail}", sol, rec))


def analyse(stacks, modules=None):
    conflicts = []
    _version_conflicts(stacks, "packages", "version", conflicts)
    _version_conflicts(stacks, "runtimes", "runtime", conflicts)

    runtimes = {}
    for app, st in stacks.items():
        for rt in st["runtimes"]:
            if rt in ("node", "python", "ruby", "java", "go", "dotnet", "php"):
                runtimes.setdefault(rt, []).append(app)
    if len(runtimes) > 1:
        detail = "; ".join(f"{rt}: {', '.join(sorted(a))}" for rt, a in sorted(runtimes.items()))
        apps = [a for a_list in runtimes.values() for a in a_list]
        sol, rec = guide(GUIDE, "runtime-mix")
        conflicts.append(make_conflict("dependency", "runtime-mix", "backend-runtime", apps,
                                       "medium", f"Several runtimes: {detail}", sol, rec))

    for layer, known in FRAMEWORK_LAYERS.items():
        found = {}
        for app, st in stacks.items():
            for pkg in st["packages"]:
                if pkg in known:
                    found.setdefault(known[pkg], set()).add(app)
        if len(found) > 1:
            detail = "; ".join(f"{fw} ({', '.join(sorted(a))})" for fw, a in sorted(found.items()))
            apps = [a for s in found.values() for a in s]
            top = max(len(a) for a in found.values())
            leaders = sorted(fw for fw, a in found.items() if len(a) == top)
            sol, _ = guide(GUIDE, "framework")
            rec = (f"One {layer}; {leaders[0]} is used by the most sources" if len(leaders) == 1 else
                   f"One {layer}; {' and '.join(leaders)} are tied, so choose on the project's needs and the "
                   "team's skills")
            conflicts.append(make_conflict(
                "dependency", "framework", layer.replace(" ", "-"), apps, "medium",
                f"Competing {layer}s: {detail}", sol, rec))

    for job, pkgs in DUPLICATE_GROUPS.items():
        found = {}
        for app, st in stacks.items():
            for pkg in pkgs:
                if pkg in st["packages"]:
                    found.setdefault(pkg, set()).add(app)
        if len(found) > 1:
            detail = "; ".join(f"{p} ({', '.join(sorted(a))})" for p, a in sorted(found.items()))
            apps = [a for s in found.values() for a in s]
            sol, rec = guide(GUIDE, "duplicate-library")
            conflicts.append(make_conflict("dependency", "duplicate-library", job.replace(" ", "-").lower(),
                                           apps, "low", f"Several {job}s: {detail}", sol, rec))

    for cyc in find_cycles(modules or {}):
        sol, rec = guide(GUIDE, "circular-module")
        conflicts.append(make_conflict("dependency", "circular-module", "->".join(cyc), [], "critical",
                                       "Planned modules depend on each other in a loop: " + " -> ".join(cyc),
                                       sol, rec))
    return conflicts


NODE_BUILTINS = {"assert", "buffer", "child_process", "cluster", "crypto", "dgram", "dns", "events", "fs", "http",
                 "http2", "https", "net", "os", "path", "perf_hooks", "process", "querystring", "readline",
                 "stream", "string_decoder", "timers", "tls", "tty", "url", "util", "v8", "vm", "worker_threads",
                 "zlib", "module", "async_hooks", "inspector", "test"}
PY_STDLIB_FALLBACK = {"os", "sys", "re", "json", "time", "datetime", "math", "random", "subprocess", "typing",
                      "collections", "itertools", "functools", "pathlib", "logging", "unittest", "argparse",
                      "hashlib", "hmac", "secrets", "sqlite3", "threading", "uuid", "urllib", "http", "csv",
                      "io", "tempfile", "shutil", "abc", "dataclasses", "enum", "copy", "string", "textwrap",
                      "traceback", "base64", "decimal", "statistics", "getpass", "socket", "ssl", "email", "xml"}
TOOLING = ("typescript", "eslint", "prettier", "jest", "vitest", "mocha", "webpack", "vite", "rollup", "esbuild",
           "babel", "@babel/", "@types/", "nodemon", "ts-node", "tsx", "husky", "lint-staged", "pytest", "black",
           "flake8", "ruff", "mypy", "isort", "coverage", "tox", "pre-commit", "setuptools", "wheel", "pip",
           "react-dom", "@testing-library/", "supertest", "jest-junit")
PY_IMPORT_NAMES = {"pyyaml": "yaml", "beautifulsoup4": "bs4", "pillow": "pil", "scikit-learn": "sklearn",
                   "python-dateutil": "dateutil", "opencv-python": "cv2", "psycopg2-binary": "psycopg2"}


def _norm_pkg(name):
    n = name.lower()
    return PY_IMPORT_NAMES.get(n, n).replace("-", "_")


def parse_audit(path, app):
    """Confirmed vulnerabilities from npm audit, pip-audit or osv-scanner JSON."""
    data = load_json(path)
    found = []
    if isinstance(data, dict) and isinstance(data.get("vulnerabilities"), dict):
        for name, v in data["vulnerabilities"].items():
            ids = [x.get("url") or str(x.get("source")) for x in v.get("via", []) if isinstance(x, dict)]
            found.append({"app": app, "package": name, "severity": v.get("severity", "unknown"),
                          "ids": ids, "tool": "npm audit"})
    elif isinstance(data, list) or (isinstance(data, dict) and "dependencies" in data):
        deps = data if isinstance(data, list) else data["dependencies"]
        for d in deps:
            for v in d.get("vulns", []):
                found.append({"app": app, "package": d.get("name"), "version": d.get("version"),
                              "severity": "unknown", "ids": [v.get("id")], "tool": "pip-audit"})
    elif isinstance(data, dict) and "results" in data:
        for res in data["results"]:
            for p in res.get("packages", []):
                for v in p.get("vulnerabilities", []):
                    sev = ((v.get("database_specific") or {}).get("severity") or "unknown").lower()
                    found.append({"app": app, "package": (p.get("package") or {}).get("name"), "severity": sev,
                                  "ids": [v.get("id")], "tool": "osv-scanner"})
    else:
        raise ValueError(f"{path}: not npm audit, pip-audit or osv-scanner JSON")
    for f in found:
        f["status"] = "confirmed"
    return found


def audits(mixer_dir, extra=()):
    found = []
    folder = os.path.join(mixer_dir, "compat", "audit") if mixer_dir else None
    if folder and os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.endswith(".json") and "-" in name:
                found += parse_audit(os.path.join(folder, name), name.split("-", 1)[0])
    for app, path in extra:
        found += parse_audit(path, app)
    return found


def unverified_warnings(stacks):
    out = []
    for app, st in sorted(stacks.items()):
        for name, spec in sorted(st["packages"].items()):
            s = str(spec).strip().lower()
            reason = None
            if s in ("", "*", "x", "latest"):
                reason = "not pinned to a version"
            elif s.startswith(("git", "http", "file:", "link:")):
                reason = "installed from outside the package registry"
            if reason:
                out.append({"app": app, "package": name, "spec": spec, "status": "unverified", "reason": reason})
    return out


def necessity(mixer_dir, stacks, kept_features=None):
    """Per app: possibly unused, undeclared, and only-used-by-dropped-features packages."""
    if not mixer_dir:
        return {}
    project = load_json(os.path.join(mixer_dir, "project.json"))
    stdlib = set(getattr(sys, "stdlib_module_names", ())) or PY_STDLIB_FALLBACK
    out = {}
    for src in project.get("sources", []):
        idx_path = os.path.join(mixer_dir, "sources", f"{src['id']}-{src['slug']}", "index.json")
        if not os.path.exists(idx_path) or src["id"] not in stacks:
            continue
        index = load_json(idx_path)
        langs = {f["path"]: f["language"] for f in index.get("files", [])}
        imported = {}
        for pkg, files in index.get("external_imports", {}).items():
            py = all(langs.get(f) == "python" for f in files)
            if (py and pkg in stdlib) or (not py and pkg in NODE_BUILTINS):
                continue
            imported[_norm_pkg(pkg)] = (pkg, files)
        declared = {_norm_pkg(n): n for n in stacks[src["id"]]["packages"]}
        tooling = lambda n: any(n == t or (t.endswith("/") and n.startswith(t)) or n.startswith(t + "-")  # noqa
                                for t in TOOLING)
        unused = sorted(n for k, n in declared.items() if k not in imported and not tooling(n))
        undeclared = sorted(pkg for k, (pkg, _) in imported.items() if k not in declared)
        dropped_only = []
        ff = index.get("feature_files") or {}
        if kept_features is not None and ff:
            owners = {}
            for fid, files in ff.items():
                for f in files:
                    owners.setdefault(f, set()).add(fid)
            for k, (pkg, files) in sorted(imported.items()):
                if all(owners.get(f) for f in files) and not any(owners[f] & kept_features for f in files):
                    dropped_only.append(pkg)
        out[src["id"]] = {"possibly_unused": unused, "undeclared": undeclared, "only_dropped_features": dropped_only,
                          "status": "unverified (import scanning is approximate)"}
    return out


VULN_SEVERITY = {"critical": "high", "high": "high", "moderate": "medium", "medium": "medium", "low": "low",
                 "info": "info", "unknown": "medium"}


def vulnerability_conflicts(vulns):
    out = []
    for v in vulns:
        sev = VULN_SEVERITY.get(str(v["severity"]).lower(), "medium")
        out.append(make_conflict(
            "dependency", "vulnerability", f"{v['app']}:{v['package']}", [v["app"]], sev,
            f"{v['tool']} reports {v['package']} as {v['severity']} ({', '.join(map(str, v['ids'])) or 'no id'})",
            ["Upgrade to a fixed version", "Replace the package", "Drop the package if no kept feature needs it"],
            "Use a fixed version in the unified app, or leave the package out"))
    return out


def kept_source_features(mixer_dir):
    path = os.path.join(mixer_dir, "feature-menu.csv") if mixer_dir else None
    if not path or not os.path.exists(path):
        return None
    from validate_feature_menu import load
    from mixerlib import split_ids
    return {f for r in load(path) if r.get("pick", "").lower() == "keep" for f in split_ids(r.get("source_features"))}


def render(conflicts):
    if not conflicts:
        return "no dependency conflicts found"
    order = {s: i for i, s in enumerate(("critical", "high", "medium", "low", "info"))}
    lines = []
    for c in sorted(conflicts, key=lambda c: (order[c["severity"]], c["id"])):
        status = c.get("status", "open")
        lines.append(f"[{c['severity']}] {c['id']} ({status})")
        lines.append(f"    {c['detail']}")
        lines.append(f"    recommended: {c['recommended']}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare source app technology stacks.")
    parser.add_argument("mixer_dir", nargs="?")
    parser.add_argument("--scan", action="append", default=[], metavar="APP=PATH")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="also fail on unresolved high conflicts")
    parser.add_argument("--audit", action="append", default=[], metavar="APP=FILE",
                        help="audit tool JSON output for an app (npm audit, pip-audit, osv-scanner)")
    args = parser.parse_args(argv)

    try:
        stacks, modules, resolutions = {}, {}, {}
        if args.mixer_dir:
            stacks = collect(args.mixer_dir)
            modules = planned_modules(args.mixer_dir)
            resolutions = load_resolutions(args.mixer_dir)
        for item in args.scan:
            if "=" not in item:
                raise ValueError(f"--scan needs APP=PATH, got '{item}'")
            app, path = item.split("=", 1)
            if not os.path.isdir(path):
                raise ValueError(f"not a folder: {path}")
            stacks[app] = scan_manifests(path)
        if not stacks:
            raise ValueError("give a mixer folder or at least one --scan APP=PATH")
        extra = []
        for item in args.audit:
            if "=" not in item:
                raise ValueError(f"--audit needs APP=FILE, got '{item}'")
            extra.append(tuple(item.split("=", 1)))
        vulns = audits(args.mixer_dir, extra)
        intel = {"vulnerabilities": vulns, "warnings": unverified_warnings(stacks),
                 "necessity": necessity(args.mixer_dir, stacks, kept_source_features(args.mixer_dir))}
    except (OSError, ValueError) as e:
        print(f"error: {e}")
        return 2

    conflicts = apply_resolutions(analyse(stacks, modules) + vulnerability_conflicts(vulns), resolutions)
    stop = blocking(conflicts, args.strict)
    if args.json:
        print(json.dumps({"conflicts": conflicts, "blocking": [c["id"] for c in stop], "intelligence": intel},
                         indent=2))
    else:
        print(render(conflicts))
        print(f"vulnerabilities (confirmed by an audit tool): {len(vulns) or 'none supplied'}")
        for v in vulns:
            print(f"  [{v['severity']}] {v['app']} {v['package']} ({v['tool']}: {', '.join(map(str, v['ids'])) or '-'})")
        for w in intel["warnings"]:
            print(f"  [unverified] {w['app']} {w['package']} {w['spec']}: {w['reason']}")
        for app, n in intel["necessity"].items():
            for key, label in (("possibly_unused", "declared but not imported"), ("undeclared", "imported but not declared"),
                               ("only_dropped_features", "only used by dropped features")):
                if n[key]:
                    print(f"  [suggestion] {app} {label}: {', '.join(n[key])}")
        if stop:
            print(f"{len(stop)} unresolved conflict(s) block integration")
    return 1 if stop else 0


if __name__ == "__main__":
    sys.exit(main())
