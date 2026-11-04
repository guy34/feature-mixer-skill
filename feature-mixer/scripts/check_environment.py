#!/usr/bin/env python3
"""Record what this session can actually do, before any reconnaissance.

Usage:
    python3 check_environment.py --mixer mixer/ [--target app/]
    python3 check_environment.py --mixer mixer/ --set browser=unavailable "no browser tool in this session"

The script detects what a program can see: the terminal it runs in, Python,
git, node and npm, docker or podman (for isolated runs), test runners, audit
tools, the Claude Code CLI, and write access to the target folder.

It cannot see Claude's own tools. Claude records those with --set, from
the tools the session really has:
  browser             a browser tool that can open pages and use the user's account
  web_fetch           a tool that can read public web pages
  repository_access   permission and network to clone the repositories named
  external_api        access to any external API a source needs

Statuses: available, unavailable, partial, not-needed (no input needs it;
treated as unavailable if one does), not-checked. Writes
mixer/capabilities.json and keeps earlier --set rows. Never fabricate a
capability: a missing tool is "unavailable", an untried one "not-checked".

Exit codes: 0 written, 2 bad input. Standard library only, no network.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from mixerlib import CAPABILITY_STATUS

CLAUDE_ROWS = ("browser", "web_fetch", "repository_access", "external_api")


def _version(cmd):
    path = shutil.which(cmd[0])
    if not path:
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        text = (out.stdout or out.stderr).strip().splitlines()
        return text[0][:80] if text else "found"
    except (OSError, subprocess.SubprocessError):
        return "found (version unknown)"


def row(status, detail):
    return {"status": status, "detail": detail}


def detect(target=None, base=None):
    caps = {"terminal": row("available", "check_environment.py ran in a shell")}
    tools = {
        "python": [sys.executable, "--version"],
        "git": ["git", "--version"],
        "node": ["node", "--version"],
        "npm": ["npm", "--version"],
        "docker": ["docker", "--version"],
        "podman": ["podman", "--version"],
        "pytest": ["pytest", "--version"],
        "pip-audit": ["pip-audit", "--version"],
        "osv-scanner": ["osv-scanner", "--version"],
        "claude-cli": ["claude", "--version"],
    }
    found = {name: _version(cmd) for name, cmd in tools.items()}
    caps["tools"] = {name: row("available", v) if v else row("unavailable", "not on PATH") for name, v in found.items()}
    runners = [n for n in ("python", "pytest", "node") if found.get(n)]
    caps["test_execution"] = (row("available", "can run tests with: " + ", ".join(runners)) if runners
                              else row("unavailable", "no test runner found"))
    iso = [n for n in ("docker", "podman") if found.get(n)]
    caps["isolation"] = (row("available", "containers possible with " + "/".join(iso)) if iso
                         else row("unavailable", "no container runtime; prefer a disposable VM or cloud sandbox"))
    caps["vulnerability_audit"] = (
        row("partial", "audit tools present: " + ", ".join(n for n in ("npm", "pip-audit", "osv-scanner") if found.get(n))
            + " (they need network; run only with approval)")
        if any(found.get(n) for n in ("npm", "pip-audit", "osv-scanner"))
        else row("unavailable", "no audit tool; vulnerabilities cannot be confirmed"))
    caps["filesystem_write"] = _write_check(target, base)
    caps["network"] = row("not-checked", "scripts never touch the network; Claude records this if it matters")
    return caps


def _write_check(target, base=None):
    folder = target or os.getcwd()
    probe_dir = folder if os.path.isdir(folder) else os.path.dirname(os.path.abspath(folder)) or "."
    shown = probe_dir
    if base:
        rel = os.path.relpath(os.path.abspath(probe_dir), os.path.abspath(base))
        shown = rel if not rel.startswith("..") else probe_dir
    try:
        with tempfile.NamedTemporaryFile(dir=probe_dir, prefix=".fm-write-check-"):
            pass
        return row("available", f"can write in {shown}")
    except OSError as e:
        return row("unavailable", f"cannot write in {shown}: {e.strerror}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Record this session's capabilities.")
    parser.add_argument("--mixer", required=True, help="the mixer/ folder")
    parser.add_argument("--target", help="where the app will be built")
    parser.add_argument("--set", nargs=2, action="append", default=[], metavar=("NAME=STATUS", "DETAIL"),
                        help="record a capability only Claude can see, e.g. browser=unavailable 'no browser tool'")
    args = parser.parse_args(argv)
    if not os.path.isdir(args.mixer):
        print(f"error: not a folder: {args.mixer}")
        return 2
    path = os.path.join(args.mixer, "capabilities.json")
    old = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f).get("capabilities", {})
    caps = detect(args.target, os.path.dirname(os.path.abspath(args.mixer)))
    for name in CLAUDE_ROWS:
        caps[name] = old.get(name) or row("not-checked", "Claude must record this from its own tools (--set)")
    for spec, detail in args.set:
        if "=" not in spec:
            print(f"error: --set needs NAME=STATUS, got '{spec}'")
            return 2
        name, status = spec.split("=", 1)
        if status not in CAPABILITY_STATUS:
            print(f"error: status must be one of {', '.join(CAPABILITY_STATUS)}")
            return 2
        caps[name] = row(status, detail)
    data = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "checked_by": "check_environment.py", "capabilities": caps}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    for name, r in caps.items():
        if name != "tools":
            print(f"{name:20} {r['status']:13} {r['detail']}")
    pending = [n for n in CLAUDE_ROWS if caps[n]["status"] == "not-checked"]
    if pending:
        print("still to record (Claude's own tools): " + ", ".join(pending))
    return 0


if __name__ == "__main__":
    sys.exit(main())
