#!/usr/bin/env python3
"""Index a source repository so large codebases can be analysed module by module.

Usage:
    python3 index_repo.py SOURCE_DIR --out mixer/sources/A-app/index.json
    python3 index_repo.py SOURCE_DIR --out .../index.json --previous .../index.json --source-json .../source.json

Writes, for every file (vendored, generated and git folders skipped):
path, size, SHA-256, language, module, line count, and whether it is
generated or binary. Then per module: files, lines, languages, the modules
it imports, and the external packages it imports (Python and JavaScript /
TypeScript imports are found with text patterns, so the map is approximate).

With --source-json it maps each feature to the files its evidence points at
(feature_files), which is the feature-to-file map.

With --previous it compares fingerprints and lists added, changed and
removed files, plus the features whose evidence points at any of them
(stale_features). Those features must be re-analysed.

It reads files only; it never runs anything. Exit codes: 0 written, 1 written
but some features are stale, 2 bad input. Standard library only, no network.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

SKIP_DIRS = {".git", "node_modules", "vendor", ".venv", "venv", "__pycache__", "dist", "build", ".next",
             "coverage", "target", ".tox", ".mypy_cache", ".pytest_cache", ".idea", ".vscode"}
LANG = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
        ".ts": "typescript", ".tsx": "typescript", ".rb": "ruby", ".go": "go", ".java": "java", ".kt": "kotlin",
        ".cs": "csharp", ".php": "php", ".rs": "rust", ".swift": "swift", ".sql": "sql", ".html": "html",
        ".css": "css", ".scss": "css", ".vue": "vue", ".svelte": "svelte", ".md": "markdown", ".json": "json",
        ".yml": "yaml", ".yaml": "yaml", ".toml": "toml", ".sh": "shell"}
GENERATED = (re.compile(r"\.min\.(js|css)$"), re.compile(r"\.map$"),
             re.compile(r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Cargo\.lock)$"))
CONTAINERS = ("src", "lib", "app", "server", "client", "packages", "apps", "services", "modules")
PY_IMPORT = re.compile(r"^\s*(?:from\s+(\.*[\w.]*)\s+import|import\s+([\w.]+))", re.M)
JS_IMPORT = re.compile(r"""(?:import\s[^'"]*?from\s*|import\s*\(\s*|require\s*\(\s*|^\s*import\s+)['"]([^'"]+)['"]""",
                       re.M)
JS_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def module_of(rel):
    parts = rel.split("/")
    if len(parts) == 1:
        return "(root)"
    if parts[0] in CONTAINERS and len(parts) > 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def _resolve_js(rel_file, spec, files):
    base = os.path.normpath(os.path.join(os.path.dirname(rel_file), spec)).replace("\\", "/")
    for cand in [base] + [base + e for e in JS_EXT] + [f"{base}/index{e}" for e in JS_EXT]:
        if cand in files:
            return cand
    return None


def _resolve_py(rel_file, spec, files):
    if spec.startswith("."):
        dots = len(spec) - len(spec.lstrip("."))
        base = os.path.dirname(rel_file)
        for _ in range(dots - 1):
            base = os.path.dirname(base)
        name = spec.lstrip(".").replace(".", "/")
        stem = f"{base}/{name}" if name else base
    else:
        stem = spec.replace(".", "/")
    stem = stem.strip("/")
    for cand in (f"{stem}.py", f"{stem}/__init__.py"):
        if cand in files:
            return cand
    return None


def build(root):
    root = os.path.abspath(root)
    entries, skipped, texts = {}, {}, {}
    for base, dirs, names in os.walk(root, followlinks=False):
        rel_base = os.path.relpath(base, root).replace("\\", "/")
        rel_base = "" if rel_base == "." else rel_base
        keep = []
        for d in sorted(dirs):
            rel = f"{rel_base}/{d}" if rel_base else d
            if d in SKIP_DIRS or os.path.islink(os.path.join(base, d)):
                skipped[rel] = "vendored, generated, metadata or link"
            else:
                keep.append(d)
        dirs[:] = keep
        for n in sorted(names):
            full = os.path.join(base, n)
            rel = f"{rel_base}/{n}" if rel_base else n
            if os.path.islink(full):
                skipped[rel] = "symbolic link"
                continue
            with open(full, "rb") as f:
                data = f.read()
            binary = b"\x00" in data[:8192]
            ext = os.path.splitext(n.lower())[1]
            entry = {"path": rel, "size": len(data), "sha256": sha256_bytes(data), "language": LANG.get(ext, "other"),
                     "module": module_of(rel), "binary": binary,
                     "generated": any(p.search(rel) for p in GENERATED)}
            if not binary:
                text = data.decode("utf-8", errors="replace")
                entry["lines"] = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
                if ext == ".py" or ext in JS_EXT:
                    texts[rel] = text
            entries[rel] = entry

    modules, external = {}, {}
    for rel, e in entries.items():
        m = modules.setdefault(e["module"], {"files": 0, "lines": 0, "languages": set(), "depends_on": set(),
                                             "external": set()})
        m["files"] += 1
        m["lines"] += e.get("lines", 0)
        if e["language"] != "other":
            m["languages"].add(e["language"])
    for rel, text in texts.items():
        mod = entries[rel]["module"]
        ext = os.path.splitext(rel)[1]
        specs = []
        if ext == ".py":
            for a, b in PY_IMPORT.findall(text):
                specs.append(a or b)
        else:
            specs = JS_IMPORT.findall(text)
        imports, pkgs = [], []
        for spec in specs:
            if ext == ".py":
                target = _resolve_py(rel, spec, entries)
                if target is None and not spec.startswith("."):
                    pkgs.append(spec.split(".")[0])
            elif spec.startswith("."):
                target = _resolve_js(rel, spec, entries)
            else:
                target = None
                name = spec[5:] if spec.startswith("node:") else spec
                pkgs.append("/".join(name.split("/")[:2]) if name.startswith("@") else name.split("/")[0])
            if target:
                imports.append(target)
                if entries[target]["module"] != mod:
                    modules[mod]["depends_on"].add(entries[target]["module"])
        entries[rel]["imports"] = sorted(set(imports))
        entries[rel]["packages"] = sorted(set(pkgs))
        for p in set(pkgs):
            modules[mod]["external"].add(p)
            external.setdefault(p, []).append(rel)
    for m in modules.values():
        for k in ("languages", "depends_on", "external"):
            m[k] = sorted(m[k])
    return {
        "root": root,
        "indexed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "indexer": "index_repo.py",
        "totals": {"files": len(entries), "lines": sum(e.get("lines", 0) for e in entries.values()),
                   "modules": len(modules)},
        "files": [entries[k] for k in sorted(entries)],
        "modules": dict(sorted(modules.items())),
        "external_imports": {k: sorted(v) for k, v in sorted(external.items())},
        "skipped": skipped,
    }


def evidence_files(source, location_prefix=""):
    """{feature id: [file paths]} from evidence locators like 'sources/app/src/x.py:12'."""
    ev = {}
    for e in source.get("evidence", []):
        loc = e.get("locator", "")
        if loc.startswith(("http://", "https://")):
            continue
        path = re.sub(r":\d+(?:-\d+)?$", "", loc.split("#")[0]).strip()
        if location_prefix and path.startswith(location_prefix.rstrip("/") + "/"):
            path = path[len(location_prefix.rstrip("/")) + 1:]
        ev[e["id"]] = path
    out = {}
    for f in source.get("features", []):
        files = sorted({ev[r] for r in f.get("evidence", []) if r in ev})
        if files:
            out[f["id"]] = files
    return out


def source_prefixes(source):
    return [s["location"] for s in source.get("sources_used", [])
            if s.get("kind") in ("local-directory", "github", "source-code")]


def feature_files(source, index_paths):
    """Feature-to-file map, keeping only paths that exist in the index."""
    best = {}
    for prefix in source_prefixes(source) or [""]:
        for fid, files in evidence_files(source, prefix).items():
            hits = [p for p in files if p in index_paths]
            if hits:
                best.setdefault(fid, set()).update(hits)
    return {k: sorted(v) for k, v in sorted(best.items())}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Index a source repository.")
    parser.add_argument("source")
    parser.add_argument("--out", required=True)
    parser.add_argument("--previous", help="an earlier index.json, to find what changed")
    parser.add_argument("--source-json", help="the source.json, to map features to files")
    args = parser.parse_args(argv)
    if not os.path.isdir(args.source):
        print(f"error: not a folder: {args.source}")
        return 2
    index = build(args.source)
    index["root"] = os.path.relpath(index["root"], os.path.dirname(os.path.abspath(args.out)))
    paths = {f["path"] for f in index["files"]}
    source = None
    if args.source_json:
        with open(args.source_json, encoding="utf-8") as f:
            source = json.load(f)
        index["feature_files"] = feature_files(source, paths)
    stale = []
    if args.previous and os.path.exists(args.previous):
        with open(args.previous, encoding="utf-8") as f:
            old = {e["path"]: e["sha256"] for e in json.load(f).get("files", [])}
        new = {e["path"]: e["sha256"] for e in index["files"]}
        changes = {"added": sorted(set(new) - set(old)), "removed": sorted(set(old) - set(new)),
                   "changed": sorted(p for p in set(new) & set(old) if new[p] != old[p])}
        index["changes"] = changes
        touched = set(changes["removed"]) | set(changes["changed"])
        if source:
            for fid, files in (index.get("feature_files") or {}).items():
                if touched & set(files):
                    stale.append(fid)
            for prefix in source_prefixes(source) or [""]:
                for fid, files in evidence_files(source, prefix).items():
                    if set(files) & set(changes["removed"]) and fid not in stale:
                        stale.append(fid)
        index["stale_features"] = sorted(stale)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
        f.write("\n")
    t = index["totals"]
    print(f"indexed {t['files']} files, {t['lines']} lines, {t['modules']} modules -> {args.out}")
    if "changes" in index:
        c = index["changes"]
        print(f"since the previous index: {len(c['added'])} added, {len(c['changed'])} changed, "
              f"{len(c['removed'])} removed")
    if stale:
        print("re-analyse these features (their evidence changed): " + ", ".join(sorted(stale)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
