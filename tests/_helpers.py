"""Shared helpers for the Feature Mixer tests: paths and throwaway workspaces."""

import csv
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "feature-mixer")
SCRIPTS = os.path.join(SKILL, "scripts")
TEMPLATES = os.path.join(SKILL, "templates")
EXAMPLE = os.path.join(ROOT, "examples", "team-hub")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

REPORT_MD = """# Source report

## Summary
Test source.

## Sources used
## Evidence
## Features
## Data model
## Unknowns
"""

MENU_HEADER = [
    "id", "feature", "area", "source_app", "priority", "complexity", "depends_on", "conflicts_with",
    "pick", "notes", "merge_group", "merge_type", "evidence_refs", "compatibility",
    "implementation_strategy", "confidence", "integration_notes", "description", "source_features",
]


def run_script(name, *args, cwd=None):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, name), *args],
                          capture_output=True, text=True, cwd=cwd)


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def temp_menu(rows, header=MENU_HEADER):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
    f.close()
    write_csv(f.name, header, rows)
    return f.name


def row(fid, feature, **kw):
    """A v2 menu row with sensible defaults (kept, unique, evidenced)."""
    base = {
        "id": fid, "feature": feature, "area": "core", "source_app": "A", "priority": "must",
        "complexity": "S", "pick": "keep", "merge_type": "unique", "evidence_refs": "A-E01",
        "compatibility": "compatible", "implementation_strategy": "adapt", "confidence": "high",
    }
    base.update(kw)
    return base


def source_json(app, name=None, **extra):
    data = {
        "app": {"id": app, "name": name or f"App {app}"},
        "coverage": "complete",
        "sources_used": [{"ref": f"{app}-R01", "kind": "local-directory", "location": "src"}],
        "evidence": [{"id": f"{app}-E01", "source": f"{app}-R01", "basis": "observed",
                      "locator": "src/app.js:1", "summary": "Seen in the code"}],
        "features": [{"id": f"{app}-F01", "name": "Sign in", "description": "Email sign in",
                      "evidence": [f"{app}-E01"], "basis": "observed", "confidence": "high"}],
        "unknowns": [],
    }
    data.update(extra)
    return data


class Workspace:
    """A temporary project folder with mixer/ inside it."""

    def __init__(self, apps=("A", "B"), format=2):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.mixer = os.path.join(self.root, "mixer")
        os.makedirs(self.mixer)
        self.project = {"name": "Test project", "format": format, "mode": "full",
                        "target": {"path": "app"}, "sources": [], "phases": {}, "checkpoints": [],
                        "approvals": []}
        for a in apps:
            self.add_source(a)
        self.save()

    def close(self):
        self._tmp.cleanup()

    def source_folder(self, app):
        s = next(s for s in self.project["sources"] if s["id"] == app)
        return os.path.join(self.mixer, "sources", f"{app}-{s['slug']}")

    def add_source(self, app, data=None, code_reuse="allowed", access="own-code", local_path=None):
        slug = f"app-{app.lower()}"
        src = {"id": app, "name": f"App {app}", "slug": slug, "access": access, "licence": "MIT",
               "code_reuse": code_reuse, "inputs": [{"kind": "local-directory", "location": f"src/{slug}"}]}
        if local_path:
            src["local_path"] = local_path
        self.project["sources"].append(src)
        folder = self.source_folder(app)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "report.md"), "w") as f:
            f.write(REPORT_MD)
        self.set_source(app, data or source_json(app))

    def set_source(self, app, data):
        with open(os.path.join(self.source_folder(app), "source.json"), "w") as f:
            json.dump(data, f, indent=2)

    def menu(self, rows, header=MENU_HEADER):
        write_csv(os.path.join(self.mixer, "feature-menu.csv"), header, rows)

    def write_json(self, rel, data):
        path = os.path.join(self.mixer, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def phase(self, name, status="done", approved=None):
        entry = {"status": status}
        if approved is not None:
            entry["approved"] = approved
        self.project["phases"][name] = entry
        self.save()

    def done_through(self, last, approved=True):
        from mixerlib import APPROVAL_PHASES, PHASES
        for p in PHASES[:PHASES.index(last) + 1]:
            self.project["phases"][p] = {"status": "done"}
            if p in APPROVAL_PHASES:
                self.project["phases"][p]["approved"] = approved
            if p != "deployment":
                n = PHASES.index(p) + 1
                if not any(c["phase"] == p for c in self.project["checkpoints"]):
                    self.project["checkpoints"].append({"id": f"CP{n}", "phase": p, "ref": f"git:mixer-cp{n}"})
        self.save()

    def save(self):
        with open(os.path.join(self.mixer, "project.json"), "w") as f:
            json.dump(self.project, f, indent=2)

    def run(self, script, *args):
        return run_script(script, self.mixer, *args)

    def capabilities(self, **overrides):
        caps = {k: {"status": "not-needed", "detail": "test"} for k in
                ("browser", "web_fetch", "repository_access", "external_api")}
        for k in ("terminal", "filesystem_write", "test_execution"):
            caps[k] = {"status": "available", "detail": "test"}
        for k, v in overrides.items():
            caps[k] = {"status": v, "detail": "test"}
        self.write_json("capabilities.json", {"checked_at": "2026-11-04T00:00:00+00:00",
                                              "checked_by": "test", "capabilities": caps})

    def scan(self, app, high=0, acknowledged=False):
        findings = [{"kind": "secret", "severity": "high", "path": "x.py", "line": 1,
                     "detail": "aws-access-key: AKIA... (20 chars, redacted)"}] * high
        data = {"root": ".", "scanned_at": "2026-11-04T00:00:00+00:00", "scanner": "scan_source.py",
                "files_scanned": 1, "skipped": {}, "summary": {"secret": high} if high else {}, "high": high,
                "findings": findings}
        if acknowledged:
            data["acknowledged"] = True
        with open(os.path.join(self.source_folder(app), "security-scan.json"), "w") as f:
            json.dump(data, f)

    def approve(self, aid, action, target, approved=True):
        self.project["approvals"].append({"id": aid, "action": action, "target": target, "approved": approved,
                                          "by": "user", "date": "2026-11-04"})
        self.save()
