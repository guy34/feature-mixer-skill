"""Fixes for problems the benchmark runs found in 2.1 before release."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import Workspace, row, run_script, source_json  # noqa: E402

import check_compatibility as cc  # noqa: E402
import check_dependencies as cd  # noqa: E402
import scan_source  # noqa: E402
import validate_project as vp  # noqa: E402


class CheckpointTest(unittest.TestCase):
    """Runs 1, 4, 5 and 6 had to write their own snapshot script."""

    def test_make_list_restore(self):
        ws = Workspace(apps=("A",), format=3)
        self.addCleanup(ws.close)
        os.makedirs(os.path.join(ws.root, "app", "node_modules", "x"))
        with open(os.path.join(ws.root, "app", "main.py"), "w") as f:
            f.write("print(1)\n")
        r = run_script("checkpoint.py", ws.mixer, "--phase", "recon")
        self.assertEqual(r.returncode, 0, r.stdout)
        r = run_script("checkpoint.py", ws.mixer, "--phase", "implementation", "--include-target", "--note", "V1")
        self.assertIn("CP2 for implementation", r.stdout)
        with open(os.path.join(ws.mixer, "project.json")) as f:
            cps = json.load(f)["checkpoints"]
        self.assertEqual([c["id"] for c in cps], ["CP1", "CP2"])
        snap = os.path.join(ws.mixer, "checkpoints", "CP2")
        self.assertTrue(os.path.exists(os.path.join(snap, "target", "main.py")))
        self.assertFalse(os.path.exists(os.path.join(snap, "target", "node_modules")))
        self.assertFalse(os.path.exists(os.path.join(snap, "mixer", "checkpoints")))
        self.assertIn("CP1", run_script("checkpoint.py", ws.mixer, "--list").stdout)
        dest = os.path.join(ws.root, "restored")
        self.assertEqual(run_script("checkpoint.py", ws.mixer, "--restore", "CP1", "--to", dest).returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(dest, "mixer", "project.json")))
        again = run_script("checkpoint.py", ws.mixer, "--restore", "CP1", "--to", dest)
        self.assertEqual(again.returncode, 2)
        self.assertIn("already exists", again.stdout)


class SelectionModeTest(unittest.TestCase):
    """Every run: plan mode and auto-pick could not both be recorded."""

    def test_plan_with_auto_pick(self):
        ws = Workspace(apps=("A",), format=3)
        self.addCleanup(ws.close)
        ws.project.update(mode="plan", selection="auto-pick")
        ws.save()
        self.assertFalse([e for e in vp.run(ws.mixer)[0].errors if "project.json" in e])
        ws.project["selection"] = "sometimes"
        ws.save()
        self.assertTrue([e for e in vp.run(ws.mixer)[0].errors if "selection" in e])


class ScannerTest(unittest.TestCase):
    def test_short_signing_key_and_unknown_extensions(self):
        """Run 3: a 6-character JWT key was missed. Run 6: schema.prisma was not scanned."""
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "api.py"), "w") as f:
                f.write('token = jwt.encode({"sub": 1}, "secret")\nok = jwt.decode(t, os.environ["K"])\n')
            with open(os.path.join(tmp, "schema.prisma"), "w") as f:
                f.write('datasource db { url = "postgres://u:AKIA' + 'ABCDEFGHIJKLMNOP@h/db" }\n')
            result = scan_source.scan(tmp)
        by_path = {}
        for fnd in result["findings"]:
            by_path.setdefault(fnd["path"], []).append(fnd)
        self.assertEqual(len(by_path["api.py"]), 1)
        self.assertIn("literal key passed to a signing call", by_path["api.py"][0]["detail"])
        self.assertEqual(by_path["schema.prisma"][0]["kind"], "secret")


def ent(name, pk, fields, fks=(), features=()):
    return {"name": name, "primary_key": {"name": "id", "type": pk}, "fields": fields,
            "foreign_keys": list(fks), "features": list(features), "evidence": ["X-E01"], "basis": "observed"}


class CompatibilityFindingsTest(unittest.TestCase):
    def reports(self, b_ref="User"):
        a = source_json("A", features=[{"id": "A-F01", "name": "Posts", "description": "x", "evidence": ["A-E01"],
                                        "basis": "observed", "confidence": "high"}],
                        entities=[ent("User", "uuid", [{"name": "id", "type": "uuid"}]),
                                  ent("Post", "uuid", [{"name": "author_id", "type": "uuid"}],
                                      [{"field": "author_id", "references": "User"}], ["A-F01"])])
        b = source_json("B", features=[{"id": "B-F01", "name": "Login", "description": "x", "evidence": ["B-E01"],
                                        "basis": "observed", "confidence": "high"},
                                       {"id": "B-F02", "name": "Posts", "description": "x", "evidence": ["B-E01"],
                                        "basis": "observed", "confidence": "high"}],
                        entities=[ent("User", "integer primary key autoincrement",
                                      [{"name": "id", "type": "integer primary key autoincrement"}], (), ["B-F01"]),
                                  ent("Post", "integer", [{"name": "author_id", "type": "integer"},
                                                          {"name": "rating", "type": ""}],
                                      [{"field": "author_id", "references": b_ref}], ["B-F02"])])
        for d in (a, b):
            for e in d["entities"]:
                e["evidence"] = [d["evidence"][0]["id"]]
        return {"A": a, "B": b}

    def test_referenced_entities_stay_in_scope(self):
        """Run 3: users tied only to a dropped sign-in feature were left out of the comparison."""
        scope = cc.Scope({"A-F01", "B-F02"}, {"A", "B"})
        conflicts, _ = cc.analyse(self.reports(), scope)
        ids = {c["id"] for c in conflicts}
        self.assertIn("database:primary-key:user", ids)

    def test_reference_spellings(self):
        """Runs 1, 4, 5: 'User.id' and 'users(id)' produced false conflicts."""
        for ref in ("User", "User.id", "users(id)"):
            conflicts, _ = cc.analyse(self.reports(ref))
            self.assertFalse([c for c in conflicts if c["kind"] == "foreign-key"], ref)

    def test_type_strings_with_constraints(self):
        """Run 1: 'integer primary key autoincrement' was not read as integer."""
        self.assertEqual(cc.norm_type("integer primary key autoincrement"), "integer")
        self.assertEqual(cc.norm_type("VARCHAR(80) NOT NULL"), "text")
        self.assertEqual(cc.norm_type("timestamp with time zone"), "timestamp")

    def test_unknown_types_are_not_conflicts(self):
        """Run 4: unknown field types were reported as critical or high mismatches."""
        r = self.reports()
        r["A"]["entities"][1]["fields"].append({"name": "rating", "type": "integer"})
        conflicts, _ = cc.analyse(r)
        found = {c["id"]: c["severity"] for c in conflicts}
        self.assertEqual(found.get("database:unknown-type:post.rating"), "info")
        self.assertNotIn("database:field-type:post.rating", found)

    def test_affected_features_only_kept_and_manual_categories(self):
        """Run 1: dropped rows were listed as affected; manual conflicts were always 'application'."""
        ws = Workspace(apps=("A", "B"))
        self.addCleanup(ws.close)
        r = self.reports()
        ws.set_source("A", r["A"])
        ws.set_source("B", r["B"])
        ws.menu([row("M01", "Posts A", source_features="A-F01"),
                 row("M02", "Posts B", source_app="B", evidence_refs="B-E01", source_features="B-F02"),
                 row("M03", "Login B", source_app="B", evidence_refs="B-E01", source_features="B-F01", pick="drop",
                     implementation_strategy="reject")])
        ws.write_json("compat/manual-conflicts.json", [{"kind": "field-type", "subject": "post.body", "apps": ["A", "B"],
                                                        "severity": "high", "detail": "x"}])
        report = cc.run(ws.mixer)
        pk = next(c for c in report["conflicts"] if c["id"] == "database:primary-key:user")
        self.assertNotIn("M03", pk["menu_features"])
        self.assertIn("database:field-type:post.body", {c["id"] for c in report["conflicts"]})

    def test_framework_tie_is_reported_as_a_tie(self):
        """Run 6: a 1-1 tie was described as 'used by the most sources'."""
        stacks = {"A": {"packages": {"flask": "3.0"}, "runtimes": {}},
                  "B": {"packages": {"express": "^4.0.0"}, "runtimes": {}}}
        c = next(x for x in cd.analyse(stacks) if x["kind"] == "framework")
        self.assertIn("Express and Flask are tied", c["recommended"])


class MoreFindingsTest(unittest.TestCase):
    def test_runtime_from_manifest_type(self):
        """Run 6: Python (requirements.txt only) vs Node was not seen as a runtime mix."""
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            with open(os.path.join(a, "requirements.txt"), "w") as f:
                f.write("flask==3.0.0\n")
            with open(os.path.join(b, "package.json"), "w") as f:
                json.dump({"dependencies": {"express": "^4.0.0"}}, f)
            stacks = {"A": cd.scan_manifests(a), "B": cd.scan_manifests(b)}
        kinds = {c["kind"] for c in cd.analyse(stacks)}
        self.assertIn("runtime-mix", kinds)
        self.assertNotIn("runtime", kinds)  # "*" is not a version conflict

    def test_decisions_under_an_old_manual_conflict_id_still_count(self):
        """Run 1: inferring the category renamed a manual conflict and orphaned its decision."""
        ws = Workspace(apps=("A",))
        self.addCleanup(ws.close)
        ws.write_json("compat/manual-conflicts.json", [{"kind": "api", "subject": "update-semantics", "apps": ["A"],
                                                        "severity": "high", "detail": "PUT vs PATCH"}])
        ws.write_json("compat/resolutions.json", {"application:api:update-semantics":
                                                  {"decision": "PATCH", "approved": True}})
        c = next(x for x in cc.run(ws.mixer)["conflicts"] if x["subject"] == "update-semantics")
        self.assertEqual((c["id"], c["status"]), ("api:api:update-semantics", "resolved"))


if __name__ == "__main__":
    unittest.main()
