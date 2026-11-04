#!/usr/bin/env python3
"""Generate the large benchmark source (MegaCRM), reproducibly.

    python3 benchmarks/generate_large.py OUT_DIR [--seed 42]

Writes OUT_DIR/megacrm: three feature modules (contacts, deals, reports),
twenty generated filler modules of twenty files each, a vendored
node_modules folder and a dist build. Same seed, same files.
"""

import argparse
import os
import random

FEATURES = {
    "src/contacts/service.py": '''"""Contacts: create, edit, search and merge duplicate contacts."""
from src.shared.db import table

def create_contact(name, email, company=None):
    return table("contacts").insert(name=name, email=email, company=company)

def search_contacts(text):
    return table("contacts").where("name like ? or email like ?", text, text)

def merge_duplicates(keep_id, drop_id):
    """Moves deals and notes from drop_id to keep_id, then deletes drop_id."""
    table("deals").update_where("contact_id = ?", drop_id, contact_id=keep_id)
    table("contacts").delete(drop_id)
''',
    "src/contacts/schema.sql": "create table contacts (id integer primary key, name text not null, email text unique, company text);\n",
    "src/deals/pipeline.py": '''"""Deals: a sales pipeline with fixed stages."""
from src.shared.db import table
STAGES = ("lead", "qualified", "proposal", "won", "lost")

def move_deal(deal_id, stage):
    if stage not in STAGES:
        raise ValueError("unknown stage")
    return table("deals").update(deal_id, stage=stage)
''',
    "src/deals/schema.sql": "create table deals (id integer primary key, contact_id integer references contacts(id), title text, value_cents integer, stage text);\n",
    "src/reports/export.py": '''"""Reports: export contacts and deals as CSV."""
import csv
from src.shared.db import table

def export_csv(path, what="deals"):
    rows = table(what).all()
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(rows)
''',
    "src/shared/db.py": '"""Tiny table helper used by the feature modules."""\n\ndef table(name):\n    raise NotImplementedError\n',
    "README.md": "# MegaCRM\n\nContacts, a deals pipeline and CSV reports. Most of src/ is generated plumbing.\n",
    "package.json": '{"name": "megacrm-ui", "dependencies": {"react": "^18.2.0", "lodash": "^4.17.21"}}\n',
}
WORDS = ["alpha", "beta", "gamma", "delta", "omega", "sigma", "kappa", "zeta", "theta", "lambda"]


def generate(out, seed=42):
    rnd = random.Random(seed)
    root = os.path.join(out, "megacrm")
    for rel, text in FEATURES.items():
        _write(root, rel, text)
    for m in range(20):
        mod = f"gen_{WORDS[m % 10]}_{m:02d}"
        for i in range(20):
            consts = "\n".join(f"{rnd.choice(WORDS).upper()}_{j} = {rnd.randint(0, 9999)}" for j in range(5))
            _write(root, f"src/{mod}/part_{i:02d}.py",
                   f'"""Generated plumbing for {mod}; no user-facing behaviour."""\n{consts}\n\n'
                   f"def handler_{i}(payload):\n    return payload\n")
    _write(root, "node_modules/lodash/index.js", "module.exports = {};\n")
    _write(root, "dist/bundle.js", "/* built */\n")
    return root


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the large benchmark source.")
    parser.add_argument("out")
    parser.add_argument("--seed", type=int, default=42)
    a = parser.parse_args()
    print(generate(a.out, a.seed))
