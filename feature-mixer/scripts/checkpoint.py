#!/usr/bin/env python3
"""Make, list and restore checkpoints for a Feature Mixer workspace.

Usage:
    python3 checkpoint.py MIXER_DIR --phase PHASE [--note "..."] [--include-target]
    python3 checkpoint.py MIXER_DIR --list
    python3 checkpoint.py MIXER_DIR --restore CP3 --to NEW_FOLDER

A checkpoint is a copy of mixer/ (and, with --include-target, the app
folder from project.json, without node_modules, .git and caches) in
mixer/checkpoints/CP<n>/. If the project is inside a git repository, the
current commit is recorded too. Nothing is ever committed, tagged, reset or
deleted: making a checkpoint only adds a folder and a row in
project.json -> checkpoints.

Restoring copies a checkpoint into a NEW folder (which must not exist), so
the current work is never overwritten. Move it into place yourself, after
the user agrees.

Exit codes: 0 done, 2 bad input. Standard library only, no network.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from mixerlib import CHECKPOINT_PHASES, load_json, project_root

SKIP = ("checkpoints", "node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build")


def _git_head(path):
    if not shutil.which("git"):
        return None
    r = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def make(mixer_dir, phase, note="", include_target=False):
    path = os.path.join(mixer_dir, "project.json")
    project = load_json(path)
    cps = project.setdefault("checkpoints", [])
    n = max([int(c["id"][2:]) for c in cps if c["id"][2:].isdigit()] or [0]) + 1
    cid = f"CP{n}"
    dest = os.path.join(mixer_dir, "checkpoints", cid)
    if os.path.exists(dest):
        raise ValueError(f"{dest} already exists")
    shutil.copytree(mixer_dir, os.path.join(dest, "mixer"), ignore=shutil.ignore_patterns(*SKIP))
    refs = [f"snapshot:checkpoints/{cid}"]
    target = (project.get("target") or {}).get("path")
    if include_target and target:
        src = os.path.join(project_root(mixer_dir), target)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, "target"), ignore=shutil.ignore_patterns(*SKIP))
            refs.append(f"target:{target}")
    head = _git_head(project_root(mixer_dir))
    if head:
        refs.append(f"git:{head}")
    entry = {"id": cid, "phase": phase, "ref": "; ".join(refs),
             "date": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if note:
        entry["note"] = note
    cps.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2)
        f.write("\n")
    return entry


def restore(mixer_dir, cid, to):
    src = os.path.join(mixer_dir, "checkpoints", cid)
    if not os.path.isdir(src):
        raise ValueError(f"no checkpoint {cid} in {mixer_dir}/checkpoints")
    if os.path.exists(to):
        raise ValueError(f"{to} already exists; restore into a new folder")
    shutil.copytree(src, to)
    return to


def main(argv=None):
    parser = argparse.ArgumentParser(description="Feature Mixer checkpoints.")
    parser.add_argument("mixer_dir")
    parser.add_argument("--phase", choices=CHECKPOINT_PHASES)
    parser.add_argument("--note", default="")
    parser.add_argument("--include-target", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--restore", metavar="CP")
    parser.add_argument("--to")
    args = parser.parse_args(argv)
    if not os.path.exists(os.path.join(args.mixer_dir, "project.json")):
        print(f"error: {args.mixer_dir} has no project.json")
        return 2
    try:
        if args.list:
            for c in load_json(os.path.join(args.mixer_dir, "project.json")).get("checkpoints", []):
                print(f"{c['id']:5} {c['phase']:15} {c.get('date', ''):26} {c['ref']}")
        elif args.restore:
            if not args.to:
                raise ValueError("--restore needs --to NEW_FOLDER")
            print(f"restored {args.restore} into {restore(args.mixer_dir, args.restore, args.to)}")
        elif args.phase:
            e = make(args.mixer_dir, args.phase, args.note, args.include_target)
            print(f"{e['id']} for {e['phase']}: {e['ref']}")
        else:
            parser.print_help()
            return 2
    except (ValueError, OSError) as e:
        print(f"error: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
