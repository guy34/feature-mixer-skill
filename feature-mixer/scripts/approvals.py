#!/usr/bin/env python3
"""Scoped approvals for running code, and the check that enforces them.

Usage:
    python3 approvals.py request --mixer mixer/ --action run-tests --cwd app/ --unittest tests [--top .]
    python3 approvals.py request --mixer mixer/ --action run-tests --cwd app/ --junit reports/junit.xml \
        -- pytest --junitxml=reports/junit.xml
    python3 approvals.py grant   ... same scope ... --granted-by "<user's name>" --user-confirmed \
        [--expires-in 8h] [--uses 1] [--bind-code] [--note "..."]
    python3 approvals.py check   --mixer mixer/ --approval A04 ... same scope ...
    python3 approvals.py list    --mixer mixer/
    python3 approvals.py revoke  --mixer mixer/ --approval A04 --reason "..."
    python3 approvals.py approve-phase --mixer mixer/ --phase selection --granted-by "<name>" --user-confirmed

`approve-phase` records a phase approval (selection, compatibility, architecture,
deployment) with a fingerprint of what the user approved: the menu's picks and
the merge plan, the compatibility decisions, or the design. validate_project.py
reports any later change to those files as a change after approval, which must
be shown to the user and approved again (a changed requirement mid-build).

`request` prints exactly what would be approved, for Claude to show the user.
`grant` records it in project.json -> approvals, only with --user-confirmed,
which Claude passes only after the user has said yes to that exact scope.

An approval for running code is bound to:
  action       run-tests (another action never authorises test execution)
  cwd          the folder the command runs in (relative to the folder holding mixer/)
  runner       the built-in unittest harness (start and top folders), or an
               exact argument list and the JUnit file it writes
  expires_at   when it stops working (default: 8 hours after it was granted)
  max_uses     how many runs it covers (default: unlimited until it expires;
               --uses 1 makes it single-use)
  code_sha256  optional (--bind-code): a fingerprint of the folder's files,
               so the approval stops working once the code changes

run_tests.py and verify_tests.py --rerun call authorise() before executing
anything. A missing, unknown, revoked, unapproved, unscoped, mismatched,
expired or used-up approval is refused and nothing runs. Every decision,
accepted or refused, is appended to mixer/approval-log.jsonl with secrets
in the command redacted.

What this is not: proof that a human agreed. The approval record and the log
live in the workspace, and anything that can write there (including the
agent) can write a record. The check guarantees that what runs is exactly
what the record names, that it is still in force, and that every attempt is
logged; the human-consent part rests on Claude following the rule to grant
only after a clear yes. Keep project.json under version control, or copy the
log elsewhere, if you need an independent trail.

Exit codes: 0 ok / authorised, 1 refused, 2 bad input. Standard library only.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from mixerlib import APPROVAL_ACTIONS, SECRET_PATTERNS, WEAK_SECRET_PATTERN, load_json, project_root, redact

LOG_NAME = "approval-log.jsonl"
DEFAULT_EXPIRY = timedelta(hours=8)
CODE_ACTIONS = ("run-tests",)  # actions that execute code through these scripts
TREE_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".tox", ".venv", "venv",
                  "coverage", ".coverage", "htmlcov", ".next", "dist", "build", "target", ".ruff_cache"}
TREE_SKIP_SUFFIXES = (".pyc", ".pyo")


def now_utc():
    return datetime.now(timezone.utc)


def iso(t):
    return t.isoformat(timespec="seconds")


def parse_time(value):
    try:
        t = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def parse_duration(text):
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([smhd]?)\s*", str(text))
    if not m:
        raise ValueError(f"cannot read duration '{text}' (use 30m, 8h, 2d)")
    n, unit = float(m.group(1)), m.group(2) or "h"
    return timedelta(seconds=n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit])


# --- secrets in commands ------------------------------------------------------

_ARG_SECRET = re.compile(r"(?i)^(--?(?:password|passwd|pass|secret|token|api[-_]?key|access[-_]?key|auth)"
                         r"[-_a-z]*[=:])(.+)$")
_URL_CRED = re.compile(r"(\b[a-z][a-z0-9+.-]*://[^:/\s@]+:)([^@\s]+)(@)", re.I)


def redact_arg(arg):
    s = str(arg)
    m = _ARG_SECRET.match(s)
    if m:
        return m.group(1) + redact(m.group(2))
    s = _URL_CRED.sub(lambda m: m.group(1) + "(redacted)" + m.group(3), s)
    for _, pattern in SECRET_PATTERNS:
        s = re.sub(pattern, lambda m: redact(m.group(0)), s)
    s = re.sub(WEAK_SECRET_PATTERN[1], lambda m: m.group(0).replace(m.group(1), redact(m.group(1))), s)
    return s


def redact_argv(argv):
    out, hide_next = [], False
    for a in argv or []:
        if hide_next:
            out.append(redact(a))
            hide_next = False
            continue
        if re.fullmatch(r"(?i)--?(?:password|passwd|secret|token|api[-_]?key|access[-_]?key)", str(a)):
            hide_next = True
        out.append(redact_arg(a))
    return out


def argv_sha256(argv):
    return hashlib.sha256(json.dumps(list(argv or []), separators=(",", ":")).encode("utf-8")).hexdigest()


# --- code fingerprint -------------------------------------------------------------

def tree_sha256(folder, exclude=()):
    """Fingerprint of every file under folder (names and contents), skipping caches and dependencies.
    Symbolic links are fingerprinted by their target text, never followed."""
    folder = os.path.abspath(folder)
    excluded = {os.path.normcase(os.path.abspath(os.path.join(folder, e))) for e in exclude if e}
    h = hashlib.sha256()
    count = 0
    for base, dirs, files in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in TREE_SKIP_DIRS and not d.endswith(".egg-info")
                         and os.path.normcase(os.path.join(base, d)) not in excluded)
        for name in sorted(files):
            full = os.path.join(base, name)
            if name.endswith(TREE_SKIP_SUFFIXES) or os.path.normcase(full) in excluded:
                continue
            rel = os.path.relpath(full, folder).replace("\\", "/")
            h.update(rel.encode("utf-8", "surrogateescape") + b"\0")
            if os.path.islink(full):
                h.update(b"link:" + os.readlink(full).encode("utf-8", "surrogateescape"))
            else:
                try:
                    with open(full, "rb") as f:
                        for chunk in iter(lambda: f.read(1 << 16), b""):
                            h.update(chunk)
                except OSError as e:
                    h.update(f"unreadable:{e.errno}".encode())
            h.update(b"\0")
            count += 1
    return h.hexdigest(), count


def code_fingerprint(mixer_dir, cwd, junit=None):
    """tree_sha256 of the tested folder, leaving out mixer/ (when it is inside) and the results file."""
    exclude = [junit] if junit else []
    mixer_real, cwd_real = os.path.realpath(mixer_dir), os.path.realpath(cwd)
    if mixer_real == cwd_real or mixer_real.startswith(cwd_real + os.sep):
        exclude.append(os.path.relpath(mixer_real, cwd_real))
    return tree_sha256(cwd, exclude=exclude)


# --- scope ------------------------------------------------------------------------

def rel_cwd(mixer_dir, cwd):
    return os.path.relpath(os.path.realpath(cwd), os.path.realpath(project_root(mixer_dir))).replace("\\", "/")


def make_scope(mixer_dir, cwd, unittest_start=None, top=".", argv=None, junit=None, bind_code=False):
    scope = {"cwd": rel_cwd(mixer_dir, cwd)}
    if unittest_start:
        scope["runner"] = "unittest"
        scope["unittest"] = {"start": unittest_start, "top": top or "."}
    else:
        if not argv:
            raise ValueError("a command scope needs the exact command (after --)")
        scope["runner"] = "command"
        scope["argv"] = redact_argv(argv)          # for people to read; secrets never stored
        scope["argv_sha256"] = argv_sha256(argv)   # what is matched
        scope["junit"] = junit
    if bind_code:
        scope["code_sha256"] = code_fingerprint(mixer_dir, cwd, junit)[0]
    return scope


def describe_scope(scope):
    where = scope.get("cwd")
    if scope.get("runner") == "unittest":
        u = scope["unittest"]
        what = f"the Python unittest suite in {where}/{u['start']} (top folder {u['top']})"
    else:
        what = "the command " + " ".join(scope.get("argv") or []) + f" in {where}" + \
               (f", writing {scope['junit']}" if scope.get("junit") else "")
    if scope.get("code_sha256"):
        what += f"; only while the code is unchanged (fingerprint {scope['code_sha256'][:12]}...)"
    return what


def _scope_mismatch(approved, requested):
    """Why the requested scope is not the approved one, or None."""
    if not approved:
        return "the approval has no scope (an older, unscoped record), so it cannot show that it covers this command"
    if approved.get("cwd") != requested.get("cwd"):
        return f"it covers the folder '{approved.get('cwd')}', not '{requested.get('cwd')}'"
    if approved.get("runner") != requested.get("runner"):
        return f"it covers a {approved.get('runner')} run, not a {requested.get('runner')} run"
    if requested.get("runner") == "unittest":
        a, r = approved.get("unittest") or {}, requested.get("unittest") or {}
        if (a.get("start"), a.get("top", ".")) != (r.get("start"), r.get("top", ".")):
            return f"it covers unittest discovery in '{a.get('start')}', not '{r.get('start')}'"
    else:
        if approved.get("argv_sha256"):
            if approved["argv_sha256"] != requested.get("argv_sha256"):
                return "it covers a different command"
        elif list(approved.get("argv") or []) != list(requested.get("argv") or []):
            return "it covers a different command"
        if approved.get("junit") != requested.get("junit"):
            return f"it covers results written to '{approved.get('junit')}', not '{requested.get('junit')}'"
    return None


# --- ledger and log ---------------------------------------------------------------

def _project(mixer_dir):
    path = os.path.join(mixer_dir, "project.json")
    if not os.path.exists(path):
        raise ValueError(f"{path} does not exist")
    return path, load_json(path)


def _write_project(path, project):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def log_path(mixer_dir):
    return os.path.join(mixer_dir, LOG_NAME)


def read_log(mixer_dir):
    path = log_path(mixer_dir)
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        rows.append({"decision": "unreadable"})
    return rows


def uses_of(mixer_dir, approval_id):
    return sum(1 for r in read_log(mixer_dir) if r.get("approval") == approval_id and r.get("decision") == "accepted"
               and r.get("counts_as_use", True))


def append_log(mixer_dir, entry):
    entry = dict(entry, at=iso(now_utc()))
    with open(log_path(mixer_dir), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


# --- the check --------------------------------------------------------------------

class Refused(Exception):
    pass


def authorise(mixer_dir, approval_id, action, scope, cwd=None, by="run_tests.py", record=True,
              counts_as_use=True):
    """Return the approval record if approval_id authorises `action` on exactly `scope`; raise Refused otherwise.
    Every decision is logged (unless record=False, used by `approvals.py check`)."""
    entry = {"by": by, "approval": approval_id, "action": action, "cwd": scope.get("cwd"),
             "runner": scope.get("runner"),
             "command": scope.get("argv"),
             "command_sha256": scope.get("argv_sha256"),
             "unittest": scope.get("unittest"), "counts_as_use": counts_as_use}

    def refuse(reason):
        if record:
            append_log(mixer_dir, dict(entry, decision="refused", reason=reason))
        raise Refused(reason)

    try:
        _, project = _project(mixer_dir)
    except ValueError as e:
        refuse(str(e))
    if not approval_id:
        refuse("no approval given: running code needs an approval id (--approval) for exactly this command")
    ledger = [a for a in project.get("approvals", []) if a.get("id") == approval_id]
    if not ledger:
        refuse(f"approval {approval_id} is not in project.json")
    if len(ledger) > 1:
        refuse(f"approval {approval_id} is listed more than once in project.json")
    a = ledger[0]
    if a.get("action") != action:
        refuse(f"approval {approval_id} is for '{a.get('action')}', not '{action}'")
    if a.get("approved") is not True:
        refuse(f"approval {approval_id} is not approved (approved: {a.get('approved')!r})")
    if a.get("revoked_at"):
        refuse(f"approval {approval_id} was revoked at {a['revoked_at']}")
    why = _scope_mismatch(a.get("scope"), scope)
    if why:
        refuse(f"approval {approval_id} does not cover this run: {why}")
    t = now_utc()
    granted = parse_time(a.get("granted_at"))
    if granted is None:
        refuse(f"approval {approval_id} has no readable granted_at time")
    if granted > t + timedelta(minutes=5):
        refuse(f"approval {approval_id} claims to be granted in the future ({a.get('granted_at')})")
    expires = parse_time(a.get("expires_at"))
    if a.get("expires_at") and expires is None:
        refuse(f"approval {approval_id} has an unreadable expires_at")
    if expires is not None and t >= expires:
        refuse(f"approval {approval_id} expired at {a['expires_at']}")
    limit = a.get("max_uses")
    if limit is not None:
        used = uses_of(mixer_dir, approval_id)
        if used >= int(limit):
            refuse(f"approval {approval_id} allowed {limit} run(s) and has been used {used} time(s)")
    want = (a.get("scope") or {}).get("code_sha256")
    if want:
        have = code_fingerprint(mixer_dir, cwd, scope.get("junit"))[0] if cwd else None
        if have != want:
            refuse(f"approval {approval_id} covers the code as it was when approved; the files in "
                   f"{scope.get('cwd')} have changed since (fingerprint {str(have)[:12]}... vs {want[:12]}...)")
    if record:
        append_log(mixer_dir, dict(entry, decision="accepted", reason="scope, action, time and uses match"))
    return a


# --- phase approvals ------------------------------------------------------------------

PHASE_FILES = {
    "selection": ("feature-menu.csv", "merge-plan.json"),
    "compatibility": ("compat/resolutions.json", "compat/aliases.json", "compat/manual-conflicts.json"),
    "architecture": ("design/architecture.json", "design/prd.md", "design/migration-plan.md"),
    "deployment": (),
}


# Fields later phases fill in to record progress, not what the user decided. Excluded from fingerprint
# method 2, so marking a slice done or a feature verified does not look like a change to an approved decision.
PROGRESS_FIELDS = {
    "merge-plan.json": ("unified_features", ("compatibility", "validation")),
    "design/architecture.json": ("slices", ("status",)),
}
FINGERPRINT_METHOD = 2


def _decision_bytes(rel, raw, method):
    if method < 2 or rel not in PROGRESS_FIELDS:
        return raw
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return raw
    listing, fields = PROGRESS_FIELDS[rel]
    if isinstance(data, dict) and isinstance(data.get(listing), list):
        data[listing] = [{k: v for k, v in item.items() if k not in fields} if isinstance(item, dict) else item
                         for item in data[listing]]
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def phase_fingerprint(mixer_dir, phase, method=FINGERPRINT_METHOD):
    """SHA-256 over what the user approved at a phase: for selection only each row's id and pick, plus the
    merge plan; for the other phases the decision files themselves. Method 2 (2.2.1) leaves out progress
    fields (PROGRESS_FIELDS) and canonicalises JSON; method 1 hashed the files' bytes and is kept so
    approvals recorded with it still check."""
    h = hashlib.sha256()
    for rel in PHASE_FILES[phase]:
        path = os.path.join(mixer_dir, rel)
        h.update(rel.encode() + b"\0")
        if not os.path.exists(path):
            h.update(b"(absent)")
            continue
        if rel == "feature-menu.csv":
            import csv
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    h.update(f"{(row.get('id') or '').strip()}={(row.get('pick') or '').strip().lower()}\n".encode())
        else:
            with open(path, "rb") as f:
                h.update(_decision_bytes(rel, f.read(), method))
    return h.hexdigest()


def approve_phase(mixer_dir, phase, granted_by, note=""):
    path, project = _project(mixer_dir)
    entry = project.setdefault("phases", {}).setdefault(phase, {"status": "in-progress"})
    t = now_utc()
    entry.update(approved=True, date=t.date().isoformat(), approved_at=iso(t), approved_by=granted_by,
                 approved_fingerprint=phase_fingerprint(mixer_dir, phase),
                 approved_fingerprint_method=FINGERPRINT_METHOD)
    if note:
        entry["note"] = f"{entry['note']} | {note}" if entry.get("note") and note not in entry["note"] else note
    _write_project(path, project)
    append_log(mixer_dir, {"by": "approvals.py", "decision": "phase-approved", "phase": phase,
                           "granted_by": granted_by, "fingerprint": entry["approved_fingerprint"]})
    return entry


# --- CLI ----------------------------------------------------------------------------

def _scope_args(p):
    p.add_argument("--mixer", required=True)
    p.add_argument("--action", default="run-tests", choices=APPROVAL_ACTIONS)
    p.add_argument("--cwd", required=True, help="folder the command runs in")
    p.add_argument("--unittest", metavar="START_DIR")
    p.add_argument("--top", default=".")
    p.add_argument("--junit", help="JUnit XML file the command writes (relative to --cwd)")
    p.add_argument("--command-json", help="the exact command as a JSON list (alternative to -- CMD...)")


def _scope_from(args, command):
    if args.command_json:
        command = json.loads(args.command_json)
        if not isinstance(command, list) or not all(isinstance(x, str) for x in command):
            raise ValueError("--command-json must be a JSON list of strings")
    if not os.path.isdir(args.cwd):
        raise ValueError(f"--cwd is not a folder: {args.cwd}")
    if not args.unittest and not command:
        raise ValueError("give --unittest START_DIR, or the exact command after --")
    return make_scope(args.mixer, args.cwd, args.unittest, args.top, command, args.junit,
                      getattr(args, "bind_code", False))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    parser = argparse.ArgumentParser(description="Request, grant, check, list and revoke scoped approvals.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("request", "grant", "check"):
        p = sub.add_parser(name)
        _scope_args(p)
        if name == "grant":
            p.add_argument("--granted-by", required=True, help="who said yes (the user's name)")
            p.add_argument("--user-confirmed", action="store_true",
                           help="pass only after the user has said yes to this exact scope")
            p.add_argument("--expires-in", default="8h", help="30m, 8h, 2d (default 8h)")
            p.add_argument("--uses", type=int, help="number of runs it covers (default: unlimited until expiry)")
            p.add_argument("--bind-code", action="store_true", help="stop working once the code changes")
            p.add_argument("--note", default="")
            p.add_argument("--id", help="approval id to use (default: the next A0n)")
        if name == "check":
            p.add_argument("--approval", required=True)
    p = sub.add_parser("approve-phase", help="record the user's yes to a phase, with a fingerprint of what they saw")
    p.add_argument("--mixer", required=True)
    p.add_argument("--phase", required=True, choices=sorted(PHASE_FILES))
    p.add_argument("--granted-by", required=True)
    p.add_argument("--user-confirmed", action="store_true")
    p.add_argument("--note", default="")
    p = sub.add_parser("list")
    p.add_argument("--mixer", required=True)
    p = sub.add_parser("revoke")
    p.add_argument("--mixer", required=True)
    p.add_argument("--approval", required=True)
    p.add_argument("--reason", default="")
    args = parser.parse_args(argv)

    try:
        if args.cmd in ("request", "grant", "check"):
            scope = _scope_from(args, command)
        if args.cmd == "request":
            print(f"Approval needed for action '{args.action}': {describe_scope(scope)}.")
            print("Ask the user for a clear yes to exactly this, then run the same command with 'grant'.")
            print(json.dumps({"action": args.action, "scope": scope}, indent=2))
            return 0
        if args.cmd == "grant":
            if not args.user_confirmed:
                print("refused: pass --user-confirmed only after the user has said yes to this exact scope")
                return 1
            if args.uses is not None and args.uses < 1:
                raise ValueError("--uses must be 1 or more")
            path, project = _project(args.mixer)
            ids = [a.get("id", "") for a in project.get("approvals", [])]
            numbers = [int(i[1:]) for i in ids if re.fullmatch(r"A\d+", i)]
            aid = args.id or "A%02d" % (max(numbers + [0]) + 1)
            if aid in ids:
                raise ValueError(f"approval {aid} already exists")
            t = now_utc()
            record = {"id": aid, "action": args.action, "target": describe_scope(scope), "approved": True,
                      "by": args.granted_by, "date": t.date().isoformat(), "granted_at": iso(t),
                      "expires_at": iso(t + parse_duration(args.expires_in)), "scope": scope,
                      "granted_via": "approvals.py grant --user-confirmed"}
            if args.uses is not None:
                record["max_uses"] = args.uses
            if args.note:
                record["note"] = args.note
            project.setdefault("approvals", []).append(record)
            _write_project(path, project)
            append_log(args.mixer, {"by": "approvals.py", "approval": aid, "action": args.action,
                                    "decision": "granted", "granted_by": args.granted_by,
                                    "scope": scope, "expires_at": record["expires_at"], "max_uses": args.uses})
            print(f"granted {aid}: {record['target']} (expires {record['expires_at']}"
                  + (f", {args.uses} use(s)" if args.uses else "") + ")")
            return 0
        if args.cmd == "check":
            try:
                authorise(args.mixer, args.approval, args.action, scope, cwd=args.cwd, record=False)
            except Refused as e:
                print(f"refused: {e}")
                return 1
            print(f"{args.approval} authorises this run")
            return 0
        if args.cmd == "approve-phase":
            if not args.user_confirmed:
                print("refused: pass --user-confirmed only after the user has approved this phase")
                return 1
            e = approve_phase(args.mixer, args.phase, args.granted_by, args.note)
            print(f"phase {args.phase} approved by {args.granted_by} (fingerprint {e['approved_fingerprint'][:12]}...)")
            return 0
        path, project = _project(args.mixer)
        if args.cmd == "list":
            for a in project.get("approvals", []):
                state = "revoked" if a.get("revoked_at") else "approved" if a.get("approved") else "not approved"
                extra = ""
                if a.get("scope") is None and a.get("action") in CODE_ACTIONS:
                    extra = " [unscoped: refused by run_tests.py]"
                if a.get("max_uses") is not None:
                    extra += f" [{uses_of(args.mixer, a['id'])} of {a['max_uses']} use(s)]"
                print(f"{a.get('id')} {a.get('action')} {state} until {a.get('expires_at', 'no expiry')}: "
                      f"{a.get('target')}{extra}")
            return 0
        if args.cmd == "revoke":
            hit = [a for a in project.get("approvals", []) if a.get("id") == args.approval]
            if not hit:
                raise ValueError(f"approval {args.approval} is not in project.json")
            hit[0]["revoked_at"] = iso(now_utc())
            if args.reason:
                hit[0]["revoked_reason"] = args.reason
            _write_project(path, project)
            append_log(args.mixer, {"by": "approvals.py", "approval": args.approval, "decision": "revoked",
                                    "reason": args.reason})
            print(f"revoked {args.approval}")
            return 0
    except (ValueError, OSError) as e:
        print(f"error: {e}")
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
