"""Evidence integrity helpers for run_tests.py and verify_tests.py.

What these give, and what they do not:
  - fingerprints (SHA-256) detect a change to a file relative to a fingerprint
    you already trust; they say nothing about whether the content was genuine
    in the first place
  - the run ledger (mixer/test-runs/ledger.jsonl) is append-only by
    convention and hash-chained: rewriting or removing an earlier run breaks
    the chain unless every later entry is rewritten too
  - an evidence key (HMAC-SHA256, a key file kept outside mixer/) makes a
    consistent rewrite of the evidence detectable by anyone holding the key,
    as long as the writer of the forgery does not have the key. If the agent
    that writes the evidence can also read the key, the key proves nothing
  - an external copy (--evidence-copy DIR) is only as independent as DIR
  - nothing here proves a human agreed to anything, or that tests were not
    written to pass trivially; --rerun with approval is the strongest check
Standard library only.
"""

import hashlib
import hmac as _hmac
import json
import os
import shutil
import socket
import stat
import time
from datetime import datetime, timezone

LEDGER = "ledger.jsonl"
LOCK = ".lock"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def atomic_write_text(path, text):
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def atomic_write_json(path, data):
    atomic_write_text(path, json.dumps(data, indent=2) + "\n")


def make_read_only(path):
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    except OSError:
        pass


# --- evidence key -------------------------------------------------------------------

def load_key(path, mixer_dir):
    """Return (key bytes, key_id, warning or None). The key must live outside mixer/."""
    if not path:
        return None, None, None
    real = os.path.realpath(path)
    mixer_real = os.path.realpath(mixer_dir)
    if real == mixer_real or real.startswith(mixer_real + os.sep):
        raise ValueError("the evidence key must be stored outside mixer/, or it protects nothing")
    with open(real, "rb") as f:
        key = f.read().strip()
    if len(key) < 16:
        raise ValueError("the evidence key is shorter than 16 bytes")
    root_real = os.path.dirname(mixer_real)
    warning = None
    if real.startswith(root_real + os.sep):
        warning = "the evidence key is inside the project folder; anything that can edit the project can read it"
    return key, hashlib.sha256(key).hexdigest()[:16], warning


def sign(key, data):
    return _hmac.new(key, canonical(data), hashlib.sha256).hexdigest()


def signature_ok(key, data, signature):
    return _hmac.compare_digest(sign(key, data), str(signature or ""))


# --- ledger -------------------------------------------------------------------------

def ledger_path(mixer_dir):
    return os.path.join(mixer_dir, "test-runs", LEDGER)


def read_ledger(mixer_dir):
    path = ledger_path(mixer_dir)
    if not os.path.exists(path):
        return None
    rows = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                rows.append({"_unreadable_line": n})
    return rows


def _entry_hash(entry):
    body = {k: v for k, v in entry.items() if k not in ("entry_sha256", "hmac")}
    return hashlib.sha256(canonical(body)).hexdigest()


def append_ledger(mixer_dir, run_id, run_record_sha256, key=None):
    rows = read_ledger(mixer_dir) or []
    prev = rows[-1].get("entry_sha256", "") if rows else ""
    entry = {"seq": len(rows) + 1, "run_id": run_id, "run_record_sha256": run_record_sha256, "prev": prev,
             "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    entry["entry_sha256"] = _entry_hash(entry)
    if key:
        entry["hmac"] = _hmac.new(key, entry["entry_sha256"].encode(), hashlib.sha256).hexdigest()
    path = ledger_path(mixer_dir)
    if os.path.exists(path):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    make_read_only(path)
    return entry


def check_ledger(mixer_dir, key=None):
    """Return (problems, {run_id: entry}) for the chain. problems is a list of strings."""
    rows = read_ledger(mixer_dir)
    if rows is None:
        return None, {}
    problems, by_run, prev = [], {}, ""
    for i, row in enumerate(rows, start=1):
        if "_unreadable_line" in row:
            problems.append(f"ledger line {row['_unreadable_line']} is not valid JSON")
            continue
        if row.get("seq") != i:
            problems.append(f"ledger entry {i} has sequence number {row.get('seq')}: entries were removed or reordered")
        if row.get("prev", "") != prev:
            problems.append(f"ledger entry {i} ({row.get('run_id')}) does not chain to the entry before it")
        if row.get("entry_sha256") != _entry_hash(row):
            problems.append(f"ledger entry {i} ({row.get('run_id')}) was edited after it was written")
        if key is not None and "hmac" in row:
            want = _hmac.new(key, str(row.get("entry_sha256")).encode(), hashlib.sha256).hexdigest()
            if not _hmac.compare_digest(want, str(row.get("hmac"))):
                problems.append(f"ledger entry {i} ({row.get('run_id')}) has a signature the evidence key "
                                "does not match")
        prev = row.get("entry_sha256", "")
        if row.get("run_id") in by_run:
            problems.append(f"run {row.get('run_id')} is in the ledger twice")
        by_run[row.get("run_id")] = row
    return problems, by_run


# --- one run at a time ----------------------------------------------------------------

def _pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if os.name == "nt":
        import subprocess
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class RunLock:
    """An exclusive lock on mixer/test-runs so two runs cannot write the same report at once."""

    def __init__(self, mixer_dir, stale_after=24 * 3600):
        self.dir = os.path.join(mixer_dir, "test-runs")
        self.path = os.path.join(self.dir, LOCK)
        self.stale_after = stale_after
        self.took_over = None

    def __enter__(self):
        os.makedirs(self.dir, exist_ok=True)
        info = {"pid": os.getpid(), "host": socket.gethostname(), "since": time.time()}
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except FileExistsError:
                try:
                    with open(self.path, encoding="utf-8") as f:
                        held = json.load(f)
                except (OSError, ValueError):
                    held = {}
                same_host = held.get("host") == socket.gethostname()
                old = time.time() - float(held.get("since", 0) or 0) > self.stale_after
                if (same_host and not _pid_alive(held.get("pid"))) or old:
                    self.took_over = held
                    try:
                        os.remove(self.path)
                    except FileNotFoundError:
                        pass
                    continue
                raise ValueError(f"another test run (pid {held.get('pid')} on {held.get('host')}) is writing to "
                                 f"{self.dir}; wait for it to finish")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(info, f)
            return self
        raise ValueError(f"could not take the run lock {self.path}")

    def __exit__(self, *exc):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        return False


# --- external copy ----------------------------------------------------------------------

def copy_run(run_dir, dest_root):
    dest = os.path.join(dest_root, os.path.basename(run_dir))
    os.makedirs(dest_root, exist_ok=True)
    if os.path.exists(dest):
        raise ValueError(f"{dest} already exists; evidence copies are never overwritten")
    shutil.copytree(run_dir, dest)
    return dest
