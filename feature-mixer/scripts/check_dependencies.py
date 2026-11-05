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

Manifests read: package.json (dependencies, dev, peer and optional), requirements*.txt
(with -r includes inside the source, -e and URL requirements), pyproject.toml
(PEP 621 and Poetry), Cargo.toml and go.mod, plus runtime.txt, .python-version,
.nvmrc and engines/requires-python. Links, oversized (over 5 MB) and malformed
manifests are not read and are listed under manifest_problems.

Version checks use real range arithmetic (versions.py): every constraint on a
package across the kept apps must leave at least one version (">=16 <20" and
"^18.2" agree; "~18.0" and "^18.2" do not). Peer and optional constraints
count; dev-only ones do not. Specs nothing offline can read (git, URLs, local
paths, workspace:, tags) are reported as uncertain, never as compatible.

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
import versions

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

SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "dist", "build", "__pycache__", ".next", "target", "vendor"}
REQ_LINE = re.compile(r"^([A-Za-z0-9_.\-\[\],]+)\s*(.*)$")
VERSION = re.compile(r"(\d+)")
MAX_MANIFEST_BYTES = 5 * 1024 * 1024
DEP_KINDS_NPM = (("dependencies", "dependency"), ("devDependencies", "dev"), ("peerDependencies", "peer"),
                 ("optionalDependencies", "optional"))


def pep503(name):
    return re.sub(r"[-_.]+", "-", name).lower()


# --- reading manifests ------------------------------------------------------

def _read_manifest(path, problems, root):
    """Text of a manifest, or None (with a problem recorded) when it is a link, too large or unreadable."""
    rel = os.path.relpath(path, root)
    if os.path.islink(path):
        problems.append({"file": rel, "problem": "manifest is a symbolic link; not followed"})
        return None
    try:
        size = os.path.getsize(path)
        if size > MAX_MANIFEST_BYTES:
            problems.append({"file": rel, "problem": f"manifest is too large ({size} bytes); not read"})
            return None
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        problems.append({"file": rel, "problem": f"cannot be read ({e.strerror})"})
        return None


def _toml(text):
    try:
        import tomllib  # Python 3.11+ (guarded)  # novermin
        return tomllib.loads(text)
    except ImportError:
        return None
    except Exception:  # tomllib.TOMLDecodeError
        return {}


def _toml_table_lines(text, table):
    """Fallback for Python < 3.11: key = value lines of one [table]."""
    m = re.search(r"^\[" + re.escape(table) + r"\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    out = {}
    if m:
        for k, v in re.findall(r'^\s*([A-Za-z0-9_.-]+)\s*=\s*(.+?)\s*$', m.group(1), re.M):
            vm = re.search(r'version\s*=\s*"([^"]*)"', v) or re.match(r'"([^"]*)"', v)
            out[k] = vm.group(1) if vm else v.strip()
    return out


def _add(stack, name, spec, kind, file, ecosystem):
    stack["constraints"].setdefault(name, []).append({"spec": str(spec), "kind": kind, "file": file,
                                                      "ecosystem": ecosystem})
    if kind != "dev" or name not in stack["packages"]:
        stack["packages"].setdefault(name, str(spec))


def _requirements(path, root, stack, seen, depth=0):
    text = _read_manifest(path, stack["problems"], root)
    if text is None or path in seen or depth > 3:
        return
    seen.add(path)
    rel = os.path.relpath(path, root)
    stack["files"].append(path)
    for raw in text.splitlines():
        line = raw.split(" #", 1)[0].split("\t#", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r ", "--requirement ", "-c ", "--constraint ")):
            inc = os.path.normpath(os.path.join(os.path.dirname(path), line.split(None, 1)[1].strip()))
            if inc.startswith(os.path.realpath(root)) or inc.startswith(root):
                if os.path.isfile(inc):
                    _requirements(inc, root, stack, seen, depth + 1)
                else:
                    stack["problems"].append({"file": rel, "problem": f"includes {line.split(None, 1)[1]}, "
                                                                      "which does not exist"})
            else:
                stack["problems"].append({"file": rel, "problem": f"includes a file outside the source: {line}"})
            continue
        if line.startswith(("-e ", "--editable ")) or re.match(r"^(?:git\+|https?://|file:|\.{0,2}/)", line):
            target = line.split(None, 1)[1] if line.startswith("-") else line
            m = re.search(r"#egg=([A-Za-z0-9_.-]+)", target) or re.search(r"([A-Za-z0-9_.-]+?)(?:\.git)?(?:@|$)",
                                                                          target.rsplit("/", 1)[-1])
            if m:
                _add(stack, pep503(m.group(1)), target, "dependency", rel, "python")
            continue
        if line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)(\[[^\]]*\])?\s*(@\s*\S+)?\s*(.*)$", line)
        if m:
            spec = (m.group(3) or m.group(4) or "").strip() or "*"
            _add(stack, pep503(m.group(1)), spec, "dependency", rel, "python")


def _pep508(req):
    m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*(\[[^\]]*\])?\s*(\(?[^;]*?\)?)?\s*(;.*)?$", req)
    if not m:
        return None, None
    spec = (m.group(3) or "").strip("() ").strip() or "*"
    if m.group(4):
        spec += " " + m.group(4).strip()
    return pep503(m.group(1)), spec


def _pyproject(path, root, stack):
    text = _read_manifest(path, stack["problems"], root)
    if text is None:
        return
    rel = os.path.relpath(path, root)
    stack["files"].append(path)
    data = _toml(text)
    if data is None:  # no tomllib: read the common tables by pattern
        for name, spec in _toml_table_lines(text, "tool.poetry.dependencies").items():
            if name.lower() == "python":
                stack["runtime_constraints"].setdefault("python", []).append({"spec": spec, "file": rel})
                stack["runtimes"].setdefault("python", spec)
            else:
                _add(stack, pep503(name), spec, "dependency", rel, "python")
        m = re.search(r"(?ms)^\[project\].*?^dependencies\s*=\s*\[(.*?)\]", text)
        for req in re.findall(r'"([^"]+)"', m.group(1) if m else ""):
            name, spec = _pep508(req)
            if name:
                _add(stack, name, spec, "dependency", rel, "python")
        m = re.search(r'(?m)^requires-python\s*=\s*"([^"]+)"', text)
        if m:
            stack["runtime_constraints"].setdefault("python", []).append({"spec": m.group(1), "file": rel})
            stack["runtimes"].setdefault("python", m.group(1))
        return
    if data == {} and text.strip():
        stack["problems"].append({"file": rel, "problem": "pyproject.toml is not valid TOML; not read"})
        return
    project = data.get("project") or {}
    for req in project.get("dependencies") or []:
        name, spec = _pep508(req)
        if name:
            _add(stack, name, spec, "dependency", rel, "python")
    for group in (project.get("optional-dependencies") or {}).values():
        for req in group:
            name, spec = _pep508(req)
            if name:
                _add(stack, name, spec, "optional", rel, "python")
    if project.get("requires-python"):
        stack["runtime_constraints"].setdefault("python", []).append({"spec": project["requires-python"],
                                                                      "file": rel})
        stack["runtimes"].setdefault("python", project["requires-python"])
    poetry = ((data.get("tool") or {}).get("poetry") or {})
    for table, kind in (("dependencies", "dependency"), ("dev-dependencies", "dev")):
        for name, v in (poetry.get(table) or {}).items():
            spec = v.get("version", "*") if isinstance(v, dict) else str(v)
            if isinstance(v, dict) and ("git" in v or "path" in v or "url" in v):
                spec = v.get("git") or v.get("path") or v.get("url")
            if name.lower() == "python":
                stack["runtime_constraints"].setdefault("python", []).append({"spec": spec, "file": rel})
                stack["runtimes"].setdefault("python", spec)
            else:
                _add(stack, pep503(name), spec, kind, rel, "python")


def _package_json(path, root, stack):
    text = _read_manifest(path, stack["problems"], root)
    if text is None:
        return
    rel = os.path.relpath(path, root)
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("not an object")
    except ValueError as e:
        stack["problems"].append({"file": rel, "problem": f"package.json is not valid JSON ({e}); not read"})
        return
    stack["files"].append(path)
    for key, kind in DEP_KINDS_NPM:
        deps = data.get(key) or {}
        if isinstance(deps, dict):
            for name, spec in deps.items():
                _add(stack, name, spec, kind, rel, "npm")
    node = (data.get("engines") or {}).get("node") if isinstance(data.get("engines"), dict) else None
    if node:
        stack["runtime_constraints"].setdefault("node", []).append({"spec": str(node), "file": rel})
        stack["runtimes"].setdefault("node", str(node))
    if data.get("workspaces"):
        stack.setdefault("workspaces", []).append(rel)


def _cargo(path, root, stack):
    text = _read_manifest(path, stack["problems"], root)
    if text is None:
        return
    rel = os.path.relpath(path, root)
    stack["files"].append(path)
    data = _toml(text)
    tables = {}
    if data is None:
        tables = {"dependencies": _toml_table_lines(text, "dependencies"),
                  "dev-dependencies": _toml_table_lines(text, "dev-dependencies")}
    else:
        tables = {k: data.get(k) or {} for k in ("dependencies", "dev-dependencies", "build-dependencies")}
    for table, deps in tables.items():
        for name, v in deps.items():
            spec = v.get("version") if isinstance(v, dict) else v
            if isinstance(v, dict) and not spec:
                spec = v.get("git") or v.get("path") or "*"
            spec = str(spec)
            if re.match(r"^\d", spec):
                spec = "^" + spec  # Cargo: "1.2" means ^1.2
            _add(stack, name, spec, "dev" if table == "dev-dependencies" else "dependency", rel, "cargo")


def _gomod(path, root, stack):
    text = _read_manifest(path, stack["problems"], root)
    if text is None:
        return
    rel = os.path.relpath(path, root)
    stack["files"].append(path)
    m = re.search(r"(?m)^go\s+(\d+\.\d+(?:\.\d+)?)", text)
    if m:
        stack["runtime_constraints"].setdefault("go", []).append({"spec": ">=" + m.group(1), "file": rel})
        stack["runtimes"].setdefault("go", m.group(1))
    reqs = re.findall(r"(?m)^\s*require\s+(\S+)\s+(v\S+)", text)
    for block in re.findall(r"(?ms)^\s*require\s*\((.*?)\)", text):
        reqs += re.findall(r"(?m)^\s*(\S+)\s+(v\S+)", block)
    for mod, ver in reqs:
        # Go picks the highest required version of a module path (minimal version selection): a minimum
        _add(stack, mod, ">=" + ver.lstrip("v").split("+")[0], "dependency", rel, "go")


def scan_manifests(path, max_depth=6):
    """Read package.json, requirements*.txt, pyproject.toml, Cargo.toml and go.mod files under path.
    Folders deeper than max_depth are not searched; that is reported as a problem, never silent."""
    stack = {"packages": {}, "constraints": {}, "runtimes": {}, "runtime_constraints": {}, "files": [],
             "problems": []}
    root = path
    base_depth = path.rstrip(os.sep).count(os.sep)
    seen = set()
    for here, dirs, names in os.walk(path, followlinks=False):
        nested = [d for d in dirs if d not in SKIP_DIRS and os.path.lexists(os.path.join(here, d, ".git"))]
        for d in nested:
            stack["problems"].append({"file": os.path.relpath(os.path.join(here, d), root), "problem":
                                      "a separate repository inside this source (its own .git); its manifests "
                                      "were not read"})
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and d not in nested
                         and not os.path.islink(os.path.join(here, d)))
        if here.count(os.sep) - base_depth >= max_depth:
            if dirs:
                stack["problems"].append({"file": os.path.relpath(here, root), "problem":
                                          f"manifests deeper than {max_depth} folders were not searched"})
            dirs[:] = []
        for n in sorted(names):
            full = os.path.join(here, n)
            if n == "package.json":
                _package_json(full, root, stack)
            elif re.fullmatch(r"requirements[\w.-]*\.(?:txt|in)", n):
                _requirements(full, root, stack, seen)
            elif n == "pyproject.toml":
                _pyproject(full, root, stack)
            elif n == "Cargo.toml":
                _cargo(full, root, stack)
            elif n == "go.mod":
                _gomod(full, root, stack)
            elif n in ("runtime.txt", ".python-version", ".nvmrc", ".node-version"):
                text = _read_manifest(full, stack["problems"], root)
                text = (text or "").strip().replace("python-", "").lstrip("v")
                if text:
                    rt = "node" if n in (".nvmrc", ".node-version") else "python"
                    stack["runtimes"].setdefault(rt, text)
                    stack["runtime_constraints"].setdefault(rt, []).append(
                        {"spec": text, "file": os.path.relpath(full, root)})
    # a manifest says which runtime the code needs even when no version is pinned
    kinds = {os.path.basename(f) for f in stack["files"]}
    if "package.json" in kinds:
        stack["runtimes"].setdefault("node", "*")
    if any(k.startswith("requirements") or k == "pyproject.toml" for k in kinds):
        stack["runtimes"].setdefault("python", "*")
    if "Cargo.toml" in kinds:
        stack["runtimes"].setdefault("rust", "*")
    if "go.mod" in kinds:
        stack["runtimes"].setdefault("go", "*")
    return stack


def _ecosystem_of(spec):
    s = str(spec)
    return "python" if re.search(r"==|~=|!=|,|;|===", s) else "npm"


def _from_report(stack, rep, app):
    """Packages and runtimes recorded in source.json (sources without a manifest: websites, API docs)."""
    for name, spec in (rep.get("packages") or {}).items():
        if name not in stack["constraints"]:
            _add(stack, name, spec, "dependency", "source.json", _ecosystem_of(spec))
    for rt, spec in (rep.get("runtimes") or {}).items():
        stack["runtimes"].setdefault(rt, str(spec))
        stack["runtime_constraints"].setdefault(rt, []).append({"spec": str(spec), "file": "source.json"})


def collect(mixer_dir):
    """Per-app stacks from project.json sources and their source.json."""
    project = load_json(os.path.join(mixer_dir, "project.json"))
    reports = load_sources(mixer_dir, project)
    root = project_root(mixer_dir)
    stacks = {}
    for s in project.get("sources", []):
        stack = {"packages": {}, "constraints": {}, "runtimes": {}, "runtime_constraints": {}, "files": [],
                 "problems": []}
        loc = s.get("local_path")
        if loc:
            path = loc if os.path.isabs(loc) else os.path.join(root, loc)
            if os.path.isdir(path):
                stack = scan_manifests(path)
                stack["files"] = [os.path.relpath(f, root) for f in stack["files"]]
        _from_report(stack, reports.get(s["id"], {}), s["id"])
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
    """v2.1 helper kept for callers: (major, open_ended) or None when the spec cannot be read."""
    s = str(spec).strip().lower()
    if not s or s in ("*", "x", "latest") or s.startswith(("git", "http", "file:", "link:", "workspace:", "npm:")):
        return None
    m = VERSION.search(s)
    if not m:
        return None
    open_ended = s.startswith(">") and "<" not in s
    return int(m.group(1)), open_ended


def versions_conflict(a, b, ecosystem=None):
    """True: no version satisfies both. False: some version does. None: cannot tell offline.
    Uses real range arithmetic (versions.py), not just the major version."""
    eco = ecosystem or (_ecosystem_of(a) if _ecosystem_of(a) == "python" or _ecosystem_of(b) == "python" else "npm")
    verdict, _ = versions.overlap(a, b, "python" if eco == "python" else "npm")
    return {"conflict": True, "compatible": False}.get(verdict)


def _eco_key(ecosystem):
    return "python" if ecosystem == "python" else "npm"


def _version_conflicts(stacks, out):
    names = sorted({n for st in stacks.values() for n in st.get("constraints", {})})
    for name in names:
        rows = []
        for app, st in sorted(stacks.items()):
            for c in st.get("constraints", {}).get(name, []):
                rows.append(dict(c, app=app))
        runtime_rows = [r for r in rows if r["kind"] != "dev"]
        apps = sorted({r["app"] for r in rows})
        if not runtime_rows:
            continue
        specs_by = {}
        for r in runtime_rows:
            specs_by.setdefault(r["spec"], []).append(r)
        if len(specs_by) < 2:
            continue
        eco = _eco_key(runtime_rows[0]["ecosystem"])
        verdict, why, unreadable = versions.all_overlap([r["spec"] for r in runtime_rows], eco)
        detail = f"{name}: " + ", ".join(f"{r['app']} uses {r['spec']}" + (f" ({r['kind']})" if r["kind"] !=
                                                                           "dependency" else "") +
                                         (f" in {r['file']}" if len({x['file'] for x in rows if x['app'] ==
                                                                     r['app']}) > 1 else "")
                                         for r in runtime_rows)
        if verdict == "conflict":
            # find the pairs that cannot both hold, for the message
            only_optional = all(r["kind"] == "optional" for r in runtime_rows if r["spec"] in specs_by)
            severity = "high" if name in FRAMEWORK_PACKAGES else "low" if only_optional else "medium"
            sol, rec = guide(GUIDE, "version")
            out.append(make_conflict("dependency", "version", name, apps, severity, f"{detail}. {why}", sol, rec))
        elif verdict == "uncertain" and len({r["app"] for r in runtime_rows}) > 1:
            out.append(make_conflict("dependency", "version-uncertain", name, apps, "low",
                                     f"{detail}. Uncertain: {why}",
                                     ["Read the referenced source or tag to find its version",
                                      "Pin a registry version in the unified app"],
                                     "Decide the version by hand; nothing offline can confirm these agree"))


def _runtime_conflicts(stacks, out):
    names = sorted({rt for st in stacks.values() for rt in st.get("runtime_constraints", {})})
    for rt in names:
        rows = [dict(c, app=app) for app, st in sorted(stacks.items())
                for c in st.get("runtime_constraints", {}).get(rt, [])]
        rows = [r for r in rows if str(r["spec"]).strip() not in ("", "*")]
        if len({r["app"] for r in rows}) < 2:
            continue
        eco = "python" if rt == "python" and any(re.search(r"~=|,|==", r["spec"]) for r in rows) else "npm"
        verdict, why, _ = versions.all_overlap([r["spec"] for r in rows], eco)
        if verdict == "conflict":
            detail = f"{rt}: " + ", ".join(f"{r['app']} uses {r['spec']}" for r in rows) + f". {why}"
            sol, rec = guide(GUIDE, "runtime")
            out.append(make_conflict("dependency", "runtime", rt, sorted({r["app"] for r in rows}), "high", detail,
                                     sol, rec))


def analyse(stacks, modules=None):
    conflicts = []
    for st in stacks.values():  # stacks built by older callers may carry only packages and runtimes
        st.setdefault("constraints", {n: [{"spec": v, "kind": "dependency", "file": "", "ecosystem":
                                           _ecosystem_of(v)}] for n, v in st.get("packages", {}).items()})
        st.setdefault("runtime_constraints", {r: [{"spec": v, "file": ""}] for r, v in st.get("runtimes", {}).items()})
    _version_conflicts(stacks, conflicts)
    _runtime_conflicts(stacks, conflicts)

    runtimes = {}
    for app, st in stacks.items():
        for rt in st["runtimes"]:
            if rt in ("node", "python", "ruby", "java", "go", "dotnet", "php", "rust"):
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
    """Specs nothing offline can check: unpinned, tags, git, URLs, local paths, workspace and alias specs."""
    out = []
    for app, st in sorted(stacks.items()):
        cons = st.get("constraints") or {n: [{"spec": v, "kind": "dependency"}] for n, v in st["packages"].items()}
        for name in sorted(cons):
            for c in cons[name]:
                s = str(c["spec"]).strip().lower()
                reason = None
                if s in ("", "*", "x", "latest") or s in versions.TAGS:
                    reason = "not pinned to a version" if s in ("", "*", "x") else f"a moving tag ({s})"
                elif s.startswith(("git", "github:", "gitlab:", "bitbucket:", "http", "file:", "link:", "-e ")):
                    reason = "installed from outside the package registry"
                elif s.startswith(("workspace:", "portal:")):
                    reason = "a package from the same repository (workspace); its version comes from that folder"
                elif s.startswith("npm:"):
                    reason = "an alias for another package; check what it points at"
                elif re.match(r"^(?:\.{0,2}/|~/)", s):
                    reason = "a local path"
                elif c.get("ecosystem") in ("npm", "python") and versions.parse(c["spec"], _eco_key(
                        c.get("ecosystem"))) is None:
                    reason = "a version spec this checker cannot read"
                if reason:
                    out.append({"app": app, "package": name, "spec": c["spec"], "kind": c.get("kind", "dependency"),
                                "status": "unverified", "reason": reason})
    return out


def manifest_problems(stacks):
    return [dict(p, app=app) for app, st in sorted(stacks.items()) for p in st.get("problems", [])]


def necessity(mixer_dir, stacks, kept_features=None):
    """Per app: possibly unused, undeclared, and only-used-by-dropped-features packages.

    Static import scanning is evidence, not proof: a package can be loaded by a plugin system, a CLI, a config
    file or a computed name. So a declared package is only called "possibly unused" when the index analysed
    every file of its language and found no dynamic import it could not resolve; otherwise it is listed as
    "not determinable" with the reason."""
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
        coverage = index.get("import_coverage") or {}
        imported = {}
        for pkg, files in index.get("external_imports", {}).items():
            py = all(langs.get(f) == "python" for f in files)
            if (py and pkg in stdlib) or (not py and pkg in NODE_BUILTINS):
                continue
            imported[_norm_pkg(pkg)] = (pkg, files)
        cons = stacks[src["id"]].get("constraints") or {}
        declared = {_norm_pkg(n): n for n in stacks[src["id"]]["packages"]}
        default_eco = "python" if "python" in coverage and not ({"javascript", "typescript"} & set(coverage)) else \
            "npm" if coverage else "unknown"
        eco_of = {_norm_pkg(n): (cons.get(n) or [{"ecosystem": default_eco}])[0].get("ecosystem", default_eco)
                  for n in declared.values()}
        tooling = lambda n: any(n == t or (t.endswith("/") and n.startswith(t)) or n.startswith(t + "-")  # noqa
                                for t in TOOLING)

        def blind_spot(eco):
            """Why imports of this ecosystem cannot rule a package out, or None."""
            names = {"python": ("python",), "npm": ("javascript", "typescript"),
                     "unknown": tuple(coverage) or ("python",)}.get(eco, ())
            if not names:
                return f"imports are not analysed for {eco} packages"
            seen = [coverage[x] for x in names if x in coverage]
            if not seen:
                return "no source file of this language was indexed" if coverage else \
                    "the index predates import coverage (re-run index_repo.py)"
            if any(c.get("unresolved_dynamic_imports") for c in seen):
                n = sum(c.get("unresolved_dynamic_imports", 0) for c in seen)
                return f"{n} dynamic import(s) with a computed name could load it"
            if any(c.get("fallback_files") for c in seen):
                return "some files could not be parsed, so their imports were read by pattern"
            if not index.get("complete", True):
                return "the index is incomplete (files skipped or unreadable)"
            return None

        unused, unknown = [], []
        for k, n in sorted(declared.items()):
            if k in imported or tooling(n):
                continue
            why = blind_spot(eco_of.get(n, default_eco))
            (unknown.append({"package": n, "why": why}) if why else unused.append(n))
        undeclared = sorted(pkg for k, (pkg, _) in imported.items() if k not in declared)
        optional = sorted({p for f in index.get("files", []) for p in f.get("optional_packages", [])})
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
        out[src["id"]] = {"possibly_unused": unused, "not_determinable": unknown,
                          "undeclared": [p for p in undeclared if p not in optional],
                          "optional_imports": optional, "only_dropped_features": dropped_only,
                          "status": "unverified (static import scanning is evidence, not proof)"}
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
                 "manifest_problems": manifest_problems(stacks),
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
        for p in intel["manifest_problems"]:
            print(f"  [not read] {p['app']} {p['file']}: {p['problem']}")
        for app, n in intel["necessity"].items():
            for key, label in (("possibly_unused", "declared but no import found"),
                               ("undeclared", "imported but not declared"),
                               ("only_dropped_features", "only used by dropped features")):
                if n[key]:
                    print(f"  [suggestion] {app} {label}: {', '.join(n[key])}")
            for item in n["not_determinable"]:
                print(f"  [unknown] {app} {item['package']}: cannot tell whether it is used ({item['why']})")
        if stop:
            print(f"{len(stop)} unresolved conflict(s) block integration")
    return 1 if stop else 0


if __name__ == "__main__":
    sys.exit(main())
