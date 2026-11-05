#!/usr/bin/env python3
"""Check the repository is ready to release, and optionally package it.

Usage (from anywhere):
    python3 tools/release_check.py                 run every check
    python3 tools/release_check.py --clean         delete caches first (__pycache__, *.pyc, .DS_Store, *.db...)
    python3 tools/release_check.py --tests         also run the test suite
    python3 tools/release_check.py --package DIR   also build the two release zips into DIR

Checks:
  caches        no __pycache__, *.pyc, .DS_Store, *.db, .pytest_cache or temp files
  versions      plugin.json, marketplace.json and the top CHANGELOG entry agree
  discovery     the plugin's "skills" paths exist and find exactly the feature-mixer skill,
                whose SKILL.md has valid name and description frontmatter
  references    every engines/, scripts/, templates/ and schemas/ path the skill mentions exists
  scripts       every script answers --help when run from an unrelated folder
  json          every schema and JSON template parses; schemas have $schema and $id
  install docs  README's install commands match the manifest names and paths
  plugin CLI    `claude plugin validate` passes (reported "not run" if the CLI is absent)
  secrets       no literal key-shaped string anywhere in the repository (fake keys in tests are assembled at
                run time), so a push is not blocked by secret scanning and nothing real ships
  tests         the test suite passes (with --tests)
  probes        every weakness probe in benchmarks/probes is defended (with --probes)

Each check prints PASS, FAIL or NOT RUN. Exit code 0 when nothing FAILs.
Standard library only.
"""

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True  # importing the scanner must not leave caches in the release
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "feature-mixer")
CACHE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
CACHE_FILES = ("*.pyc", "*.pyo", ".DS_Store", "*.db", "*.tmp", "*.swp", "Thumbs.db")
results = []


def report(name, status, detail=""):
    results.append((name, status, detail))
    print(f"{status:8} {name}" + (f": {detail}" if detail else ""))


def walk_repo():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d != ".git"]
        yield base, dirs, files


def find_caches():
    found = []
    for base, dirs, files in walk_repo():
        for d in list(dirs):
            if d in CACHE_DIRS:
                found.append(os.path.join(base, d))
                dirs.remove(d)  # its contents go with it
        for f in files:
            if any(fnmatch.fnmatch(f, p) for p in CACHE_FILES):
                found.append(os.path.join(base, f))
    return found


def clean():
    for path in find_caches():
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path):
            os.remove(path)


def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


def check_caches():
    left = find_caches()
    if left:
        report("caches", "FAIL", f"{len(left)} found, e.g. {os.path.relpath(left[0], ROOT)} (use --clean)")
    else:
        report("caches", "PASS")


def check_versions():
    plugin, market = load(".claude-plugin", "plugin.json"), load(".claude-plugin", "marketplace.json")
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        m = re.search(r"^## (\d+\.\d+\.\d+)", f.read(), re.M)
    versions = {"plugin.json": plugin.get("version"), "marketplace.json": market["plugins"][0].get("version"),
                "CHANGELOG.md": m.group(1) if m else None}
    if len(set(versions.values())) == 1 and None not in versions.values():
        report("versions", "PASS", versions["plugin.json"])
    else:
        report("versions", "FAIL", ", ".join(f"{k} {v}" for k, v in versions.items()))
    if plugin["name"] != market["plugins"][0]["name"]:
        report("names", "FAIL", "plugin.json name differs from the marketplace entry")
    else:
        report("names", "PASS", plugin["name"])
    return plugin, market


def check_discovery(plugin):
    paths = plugin.get("skills", [])
    paths = [paths] if isinstance(paths, str) else paths
    found = []
    for p in paths + ["./skills/"]:
        if p not in (".", "./") and not p.startswith("./"):
            report("discovery", "FAIL", f"skills path '{p}' must start with ./")
            return
        full = os.path.normpath(os.path.join(ROOT, p))
        if not os.path.isdir(full):
            if p != "./skills/":
                report("discovery", "FAIL", f"skills path '{p}' does not exist")
                return
            continue
        if os.path.exists(os.path.join(full, "SKILL.md")):
            found.append(full)
        for d in sorted(os.listdir(full)):
            if os.path.isfile(os.path.join(full, d, "SKILL.md")):
                found.append(os.path.join(full, d))
    names = sorted({os.path.relpath(f, ROOT) for f in found})
    if names != ["feature-mixer"]:
        report("discovery", "FAIL", f"expected exactly feature-mixer, found {names or 'nothing'}")
        return
    with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\nname: (.+)\ndescription: (.+)\n---\n", text)
    if not m or m.group(1).strip() != "feature-mixer" or len(m.group(2)) > 1024 or "<" in m.group(2):
        report("discovery", "FAIL", "SKILL.md frontmatter needs name: feature-mixer and a description under 1024 chars")
        return
    report("discovery", "PASS", "skills path finds feature-mixer/SKILL.md")


def check_references():
    text = ""
    for rel in ["SKILL.md"] + [os.path.join("engines", n) for n in os.listdir(os.path.join(SKILL, "engines"))]:
        with open(os.path.join(SKILL, rel), encoding="utf-8") as f:
            text += f.read()
    refs = sorted(set(re.findall(r"\b((?:engines|scripts|templates|schemas)/[\w.-]+\.(?:md|py|json|csv))", text)))
    missing = [r for r in refs if not os.path.isfile(os.path.join(SKILL, r))]
    report("references", "FAIL" if missing else "PASS",
           f"missing: {', '.join(missing)}" if missing else f"{len(refs)} referenced files exist")


def check_scripts():
    bad = []
    scripts = sorted(n for n in os.listdir(os.path.join(SKILL, "scripts")) if n.endswith(".py") and n != "mixerlib.py")
    with tempfile.TemporaryDirectory() as tmp:
        for name in scripts:
            r = subprocess.run([sys.executable, os.path.join(SKILL, "scripts", name), "--help"], cwd=tmp,
                               capture_output=True, text=True)
            if r.returncode != 0:
                bad.append(f"{name} (exit {r.returncode})")
    report("scripts", "FAIL" if bad else "PASS",
           ", ".join(bad) if bad else f"{len(scripts)} scripts run from an unrelated folder")


def check_json():
    bad = []
    for folder in ("schemas", "templates"):
        for name in sorted(os.listdir(os.path.join(SKILL, folder))):
            if not name.endswith(".json"):
                continue
            try:
                data = load("feature-mixer", folder, name)
            except ValueError as e:
                bad.append(f"{folder}/{name}: {e}")
                continue
            if folder == "schemas" and not ("$schema" in data and "$id" in data):
                bad.append(f"{folder}/{name}: no $schema or $id")
    report("json", "FAIL" if bad else "PASS", "; ".join(bad) if bad else "schemas and templates parse")


def check_install_docs(plugin, market):
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    m = re.search(r"github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?$", plugin.get("repository", ""))
    repo = m.group(1) if m else None
    expected = [f"/plugin marketplace add {repo}", f"/plugin install {plugin['name']}@{market['name']}",
                f"cp -r {os.path.basename(repo) if repo else '?'}/feature-mixer ~/.claude/skills/"]
    missing = [e for e in expected if e not in readme]
    report("install docs", "FAIL" if missing else "PASS",
           "README lacks: " + " | ".join(missing) if missing else "README commands match the manifests")


def check_plugin_cli():
    if not shutil.which("claude"):
        report("plugin CLI", "NOT RUN", "claude CLI not installed here")
        return
    r = subprocess.run(["claude", "plugin", "validate", ROOT], capture_output=True, text=True, timeout=120)
    out = (r.stdout + r.stderr).strip().splitlines()
    report("plugin CLI", "PASS" if r.returncode == 0 else "FAIL",
           f"claude plugin validate exit {r.returncode}: " + (out[-1] if out else "no output"))


def check_secrets():
    sys.path.insert(0, os.path.join(SKILL, "scripts"))
    import scan_source
    hits = []
    for folder in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, folder)
        if not os.path.isdir(path) or folder == ".git":
            continue
        for f in scan_source.scan(path)["findings"]:
            if f["kind"] == "secret" and not any(w in f["detail"] for w in ("split into", "base64")) and \
                    not f["detail"].startswith("connection-string"):
                hits.append(f"{folder}/{f['path']}:{f.get('line')}")
    report("secrets", "FAIL" if hits else "PASS", ", ".join(hits[:5]) if hits else "no literal key-shaped strings")


def run_probes():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "benchmarks", "probes", "run_probes.py"), SKILL, "--json"],
                       capture_output=True, text=True, timeout=900)
    try:
        res = json.loads(r.stdout)["results"]
    except (ValueError, KeyError):
        report("probes", "FAIL", "the probes did not run: " + (r.stderr or r.stdout)[-200:])
        return
    bad = [x["id"] for x in res if x["status"] != "defended"]
    report("probes", "FAIL" if bad else "PASS", f"{len(res) - len(bad)} of {len(res)} defended" +
           (f"; not defended: {', '.join(bad)}" if bad else ""))


def run_tests():
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT,
                       capture_output=True, text=True)
    tail = (r.stderr.strip().splitlines() or ["no output"])
    summary = next((line for line in reversed(tail) if line.startswith("Ran ")), tail[-1])
    report("tests", "PASS" if r.returncode == 0 else "FAIL", f"exit {r.returncode}; {summary}; {tail[-1]}")


def package(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    full = os.path.join(out_dir, "feature-mixer-skill.zip")
    skill = os.path.join(out_dir, "feature-mixer-claude-ai.zip")

    def add(z, base, arc_root):
        for b, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d not in CACHE_DIRS and d != ".git")
            for f in sorted(files):
                if any(fnmatch.fnmatch(f, p) for p in CACHE_FILES):
                    continue
                path = os.path.join(b, f)
                z.write(path, os.path.join(arc_root, os.path.relpath(path, base)))

    with zipfile.ZipFile(full, "w", zipfile.ZIP_DEFLATED) as z:
        add(z, ROOT, "feature-mixer-skill")
    with zipfile.ZipFile(skill, "w", zipfile.ZIP_DEFLATED) as z:
        add(z, SKILL, "feature-mixer")
    report("package", "PASS", f"{full} and {skill}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Release checks for Feature Mixer.")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--tests", action="store_true")
    parser.add_argument("--probes", action="store_true")
    parser.add_argument("--package", metavar="DIR")
    args = parser.parse_args(argv)
    if args.clean:
        clean()
    if args.tests:
        run_tests()
        clean() if args.clean else None
    check_caches()
    plugin, market = check_versions()
    check_discovery(plugin)
    check_references()
    check_scripts()
    check_json()
    check_install_docs(plugin, market)
    check_plugin_cli()
    check_secrets()
    if args.probes:
        run_probes()
    if args.clean:
        clean()
    failed = [r for r in results if r[1] == "FAIL"]
    if args.package and not failed:
        package(args.package)
    elif args.package:
        print("not packaging: fix the failures first")
    print(f"{len(failed)} check(s) failed" if failed else "release checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
