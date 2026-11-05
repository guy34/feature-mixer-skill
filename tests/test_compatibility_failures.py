"""Phase 3 (v2.2): the compatibility engine under pressure. Versions, imports, meaning, schemas."""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import Workspace, run_script, source_json  # noqa: E402

import check_compatibility as cc  # noqa: E402
import check_dependencies as cd  # noqa: E402
import index_repo  # noqa: E402
import versions  # noqa: E402


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text if isinstance(text, str) else json.dumps(text))
    return path


class VersionRangeTest(unittest.TestCase):
    """Test F: ranges, not major versions."""
    NPM = [
        (">=16 <20", "^18.2.0", "compatible"), ("~18.0.0", "^18.2.0", "conflict"), ("^17.0.2", "^19.0.0", "conflict"),
        ("^18.2", "18.x", "compatible"), ("*", "^19", "compatible"), (">=16,<20".replace(",", " "), "~19.1", "compatible"),
        ("^0.2.3", "^0.3.0", "conflict"), ("^0.0.3", "0.0.4", "conflict"), ("1.2.3 - 2.3", "2.3.9", "compatible"),
        ("1.2.3 - 2.3", "2.4.0", "conflict"), ("^1.2 || ^2", "2.5", "compatible"), (">1.2", "1.2.9", "conflict"),
        ("<=1.2", "1.2.5", "compatible"), ("17", "18", "conflict"), (">=18", "16.x", "conflict"),
        ("latest", "^1.0.0", "uncertain"), ("github:acme/lib#v2", "^2", "uncertain"), ("workspace:*", "^1", "uncertain"),
        ("file:../lib", "1.0.0", "uncertain"), ("npm:other@^2", "^2", "uncertain"),
        ("^18.3.0-rc.1", "^18.3", "uncertain"),
    ]
    PY = [
        (">=3.2,<4", ">=4.1", "conflict"), (">=3.2,<4", "==3.2.*", "compatible"), ("~=1.4.2", ">=1.5", "conflict"),
        ("~=2.2", "<3", "compatible"), ("==2.31.0", ">=2.0", "compatible"), ("!=1.0", "==1.0", "conflict"),
        (">=1,!=1.5", "==1.5.0", "conflict"), (">=1.0; python_version<'3.8'", "<2", "uncertain"),
        ("^1.2", ">=1.5,<1.6", "compatible"), ("git+https://x.invalid/y.git", "==1", "uncertain"),
    ]

    def test_npm_table(self):
        for a, b, want in self.NPM:
            self.assertEqual(versions.overlap(a, b)[0], want, f"{a} vs {b}")

    def test_python_table(self):
        for a, b, want in self.PY:
            self.assertEqual(versions.overlap(a, b, "python")[0], want, f"{a} vs {b}")

    def test_old_api_keeps_its_contract(self):
        self.assertFalse(cd.versions_conflict(">=16 <20", "^18.2.0"))
        self.assertTrue(cd.versions_conflict("~18.0.0", "^18.2.0"))
        self.assertIsNone(cd.versions_conflict("workspace:*", "^1"))


class DependencyManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def scan(self, **apps):
        stacks = {}
        for app, files in apps.items():
            for rel, text in files.items():
                write(os.path.join(self.tmp, app), rel, text)
            stacks[app] = cd.scan_manifests(os.path.join(self.tmp, app))
        return stacks, {(c["kind"], c["subject"]): c for c in cd.analyse(stacks)}

    def test_react_17_vs_19_and_overlapping_ranges(self):
        _, found = self.scan(A={"package.json": {"dependencies": {"react": "^17.0.2", "lodash": ">=4 <5"}}},
                             B={"package.json": {"dependencies": {"react": "^19.0.0", "lodash": "^4.17.21"}}})
        self.assertEqual(found[("version", "react")]["severity"], "high")
        self.assertIn("no version satisfies", found[("version", "react")]["detail"])
        self.assertNotIn(("version", "lodash"), found)

    def test_backend_framework_majors(self):
        _, found = self.scan(A={"requirements.txt": "Django>=3.2,<4\n"}, B={"pyproject.toml":
                             '[project]\nname="b"\ndependencies=["django>=4.2", "requests[socks]>=2.31"]\n'
                             'requires-python=">=3.10"\n'})
        self.assertIn(("version", "django"), found)

    def test_peer_and_optional_dependencies(self):
        _, found = self.scan(A={"package.json": {"dependencies": {"react": "^17.0.2"},
                                                 "optionalDependencies": {"fsevents": "^1.2.0"}}},
                             B={"package.json": {"peerDependencies": {"react": "^19.0.0"},
                                                 "optionalDependencies": {"fsevents": "^2.3.0"}}})
        self.assertIn("(peer)", found[("version", "react")]["detail"])
        self.assertEqual(found[("version", "fsevents")]["severity"], "low")

    def test_dev_only_differences_are_not_conflicts(self):
        _, found = self.scan(A={"package.json": {"devDependencies": {"jest": "^27"}}},
                             B={"package.json": {"devDependencies": {"jest": "^29"}}})
        self.assertNotIn(("version", "jest"), found)

    def test_git_local_and_workspace_specs_are_uncertain_not_dropped(self):
        stacks, found = self.scan(A={"package.json": {"dependencies": {"ui": "github:acme/ui#v2", "core": "file:../core"}}},
                                  B={"package.json": {"dependencies": {"ui": "workspace:*", "core": "^1.0.0"}}})
        self.assertEqual(found[("version-uncertain", "ui")]["severity"], "low")
        self.assertIn(("version-uncertain", "core"), found)
        reasons = {(w["app"], w["package"]): w["reason"] for w in cd.unverified_warnings(stacks)}
        self.assertIn("outside the package registry", reasons[("A", "ui")])
        self.assertIn("workspace", reasons[("B", "ui")])
        self.assertIn("outside the package registry", reasons[("A", "core")])

    def test_python_requirements_forms(self):
        stacks, _ = self.scan(A={"requirements.txt": "-r base.txt\n-e git+https://x.invalid/lib.git#egg=mylib\n"
                                                     "requests[socks]>=2.31 ; python_version >= '3.8'\n",
                                 "base.txt": "Flask==3.0.0\n"})
        c = stacks["A"]["constraints"]
        self.assertEqual(c["flask"][0]["spec"], "==3.0.0")
        self.assertIn("git+https", c["mylib"][0]["spec"])
        self.assertIn("python_version", c["requests"][0]["spec"])

    def test_monorepo_packages_with_different_versions_in_one_app(self):
        _, found = self.scan(A={"apps/web/package.json": {"dependencies": {"react": "^18.2.0"}},
                                "apps/admin/package.json": {"dependencies": {"react": "^17.0.2"}}})
        c = found[("version", "react")]
        self.assertEqual(c["apps"], ["A"])
        self.assertIn("apps/web/package.json", c["detail"])

    def test_runtime_ranges(self):
        _, found = self.scan(A={"package.json": {"engines": {"node": ">=20"}}},
                             B={"package.json": {"engines": {"node": ">=16 <20"}}},
                             C={".nvmrc": "v20.11.0\n"})
        self.assertIn(("runtime", "node"), found)
        _, ok = self.scan(D={"package.json": {"engines": {"node": ">=18"}}}, E={".nvmrc": "20\n"})
        self.assertNotIn(("runtime", "node"), ok)

    def test_cargo_and_go(self):
        stacks, found = self.scan(A={"Cargo.toml": '[dependencies]\nserde = "1.0"\ntokio = { version = "1.20" }\n'},
                                  B={"Cargo.toml": '[dependencies]\nserde = "2.0"\n'},
                                  C={"go.mod": "module example.com/c\n\ngo 1.21\n\nrequire (\n\tgithub.com/x/y v1.2.3\n)\n"})
        self.assertIn(("version", "serde"), found)
        self.assertEqual(stacks["A"]["constraints"]["serde"][0]["spec"], "^1.0")
        self.assertEqual(stacks["C"]["runtimes"]["go"], "1.21")
        self.assertIn("github.com/x/y", stacks["C"]["packages"])

    def test_pyproject_without_tomllib(self):
        real = cd._toml
        cd._toml = lambda text: None
        try:
            stacks, _ = self.scan(A={"pyproject.toml": '[project]\nname = "a"\ndependencies = ["httpx>=0.27", '
                                                       '"pydantic>=2,<3"]\nrequires-python = ">=3.9"\n'})
        finally:
            cd._toml = real
        self.assertEqual(stacks["A"]["constraints"]["pydantic"][0]["spec"], ">=2,<3")
        self.assertEqual(stacks["A"]["runtimes"]["python"], ">=3.9")

    def test_linked_and_malformed_manifests_are_reported(self):
        os.makedirs(os.path.join(self.tmp, "A"))
        write(self.tmp, "outside/package.json", {"dependencies": {"evil": "1.0.0"}})
        if os.name != "nt":
            os.symlink(os.path.join(self.tmp, "outside", "package.json"), os.path.join(self.tmp, "A", "package.json"))
        write(os.path.join(self.tmp, "A"), "sub/package.json", "{ broken")
        st = cd.scan_manifests(os.path.join(self.tmp, "A"))
        self.assertNotIn("evil", st["packages"])
        probs = " ".join(p["problem"] for p in st["problems"])
        self.assertIn("not valid JSON", probs)
        if os.name != "nt":
            self.assertIn("symbolic link", probs)


POLYGLOT = {
    "pkg/__init__.py": "",
    "pkg/a.py": "from . import b\nfrom .c import thing\nimport requests\n"
                "try:\n    import ujson as json\nexcept ImportError:\n    import json\n"
                "if FAST:\n    import orjson\n",
    "pkg/b.py": "import importlib\nyaml = importlib.import_module('yaml')\nplugin = importlib.import_module(name)\n"
                "from pkg import a\n",
    "pkg/c.py": "thing = 1\n",
    "web/tsconfig.json": {"compilerOptions": {"baseUrl": ".", "paths": {"@app/*": ["src/*"]}}},
    "web/src/index.ts": "import { x } from '@app/util';\nexport * from './barrel';\nimport React from 'react';\n"
                        "const m = await import('./lazy');\nconst p = require(pluginName);\n"
                        "import { ui } from '@acme/ui';\n",
    "web/src/util.ts": "export const x = 1;\n",
    "web/src/barrel.ts": "export { y } from './inner';\n",
    "web/src/inner.ts": "export const y = 2;\n",
    "web/src/lazy.ts": "export default 1;\n",
    "packages/ui/package.json": {"name": "@acme/ui"},
    "packages/ui/index.ts": "export const ui = 1;\n",
    "svc/go.mod": "module example.com/svc\n\ngo 1.22\n",
    "svc/main.go": 'package main\n\nimport (\n\t"fmt"\n\t"example.com/svc/internal/db"\n\t"github.com/gin-gonic/gin"\n)\n',
    "rs/src/main.rs": "use serde::Serialize;\nuse crate::models;\nextern crate rand;\n",
    "jv/src/main/java/com/acme/App.java": "import com.acme.util.Strings;\nimport org.springframework.boot.Spring;\n"
                                          "import java.util.List;\n",
    "jv/src/main/java/com/acme/util/Strings.java": "package com.acme.util;\n",
    "rb/app.rb": "require 'sinatra'\n",
}


class ImportDetectionTest(unittest.TestCase):
    """Test G: imports are evidence, not certainty; coverage is reported."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        for rel, text in POLYGLOT.items():
            write(cls.tmp, rel, text)
        cls.idx = index_repo.build(cls.tmp)
        cls.files = {f["path"]: f for f in cls.idx["files"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_python_relative_dynamic_and_optional(self):
        a, b = self.files["pkg/a.py"], self.files["pkg/b.py"]
        self.assertIn("pkg/b.py", a["imports"])
        self.assertIn("pkg/c.py", a["imports"])
        self.assertIn("requests", a["packages"])
        self.assertTrue({"ujson", "orjson"} <= set(a["optional_packages"]))  # try/except ImportError, if-block
        self.assertNotIn("requests", a["optional_packages"])
        self.assertIn("yaml", b["packages"])
        self.assertEqual(b["unresolved_dynamic_imports"], 1)

    def test_circular_imports_are_reported(self):
        a = self.files["pkg/b.py"]
        self.assertIn("pkg/a.py", a["imports"])  # a -> b -> a, inside one module: a file-level cycle
        self.assertEqual(self.idx["import_coverage"]["python"]["method"], "parsed (ast)")

    def test_typescript_aliases_barrels_workspaces_and_dynamic(self):
        f = self.files["web/src/index.ts"]
        self.assertIn("web/src/util.ts", f["imports"])        # @app/* path alias
        self.assertIn("web/src/barrel.ts", f["imports"])      # export * from
        self.assertIn("web/src/lazy.ts", f["imports"])        # import('./lazy')
        self.assertIn("packages/ui/index.ts", f["imports"])   # workspace package @acme/ui
        self.assertEqual(f["packages"], ["react"])
        self.assertEqual(f["unresolved_dynamic_imports"], 1)  # require(pluginName)
        self.assertIn("web/src/inner.ts", self.files["web/src/barrel.ts"]["imports"])

    def test_go_rust_java_and_unsupported(self):
        self.assertEqual(self.files["svc/main.go"]["packages"], ["github.com/gin-gonic/gin"])
        self.assertEqual(sorted(self.files["rs/src/main.rs"]["packages"]), ["rand", "serde"])
        self.assertEqual(self.files["jv/src/main/java/com/acme/App.java"]["packages"], ["org.springframework"])
        self.assertEqual(self.idx["import_coverage"]["ruby"]["method"], "not supported")

    def test_module_cycles(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        write(tmp, "src/orders/a.py", "from src.billing import b\n")
        write(tmp, "src/billing/b.py", "from src.orders import a\n")
        write(tmp, "src/orders/__init__.py", "")
        write(tmp, "src/billing/__init__.py", "")
        idx = index_repo.build(tmp)
        self.assertTrue(idx["module_cycles"])

    def test_no_unused_claim_when_dynamic_imports_exist(self):
        ws = Workspace(apps=("A",), format=3)
        self.addCleanup(ws.close)
        src = os.path.join(ws.root, "src")
        write(src, "app.py", "import importlib\nmod = importlib.import_module(settings.BACKEND)\n")
        write(src, "requirements.txt", "redis==5.0\ncelery==5.3\n")
        ws.project["sources"][0]["local_path"] = "src"
        ws.save()
        idx = index_repo.build(src)
        write(ws.source_folder("A"), "index.json", idx)
        stacks = cd.collect(ws.mixer)
        n = cd.necessity(ws.mixer, stacks)["A"]
        self.assertEqual(n["possibly_unused"], [])
        self.assertEqual({x["package"] for x in n["not_determinable"]}, {"redis", "celery"})
        self.assertIn("computed name", n["not_determinable"][0]["why"])


def entity(name, fields, pk_type="int", **extra):
    e = {"name": name, "primary_key": {"name": "id", "type": pk_type},
         "fields": [{"name": "id", "type": pk_type}] + fields}
    e.update(extra)
    return e


class CompatCase(unittest.TestCase):
    """Runs check_compatibility on hand-written source reports (no tests of its own)."""

    def run_compat(self, a, b, c=None, aliases=None, arch=None, **extra):
        ws = Workspace(apps=("A", "B", "C") if c is not None else ("A", "B"), format=3)
        self.addCleanup(ws.close)
        for app, ents in (("A", a), ("B", b), ("C", c)):
            if ents is None:
                continue
            ws.set_source(app, source_json(app, entities=ents, **extra.get(app, {})))
        if aliases:
            ws.write_json("compat/aliases.json", aliases)
        if arch:
            ws.write_json("design/architecture.json", arch)
        report = cc.run(ws.mixer, use_all=True)
        return {(x["kind"], x["subject"]): x for x in report["conflicts"]}, report


class SemanticConflictTest(CompatCase):
    """Test H: never merge on name alone, never assume different names differ; ask, and record why."""

    def test_user_account_member_are_offered_as_possible_aliases(self):
        found, _ = self.run_compat([entity("User", [{"name": "email", "type": "text"}])],
                                   [entity("Account", [{"name": "email", "type": "text"}])],
                                   [entity("Member", [{"name": "email", "type": "text"}])])
        pairs = {k[1] for k in found if k[0] == "possible-alias"}
        self.assertEqual(pairs, {"account~member", "account~user", "member~user"})
        self.assertNotIn("duplicate-entity", {k[0] for k in found})

    def test_alias_merges_only_with_a_recorded_reason(self):
        a = [entity("User", [{"name": "email", "type": "text"}])]
        b = [entity("Member", [{"name": "email", "type": "text"}])]
        found, _ = self.run_compat(a, b, aliases={"entities": {"Member": "User"}})
        self.assertIn(("duplicate-entity", "user"), found)
        self.assertIn(("alias-unexplained", "entities:Member->User"), found)
        found, _ = self.run_compat(a, b, aliases={"entities": {"Member": {"to": "User",
                                                                          "reason": "B's members sign in like A's users"}}})
        self.assertNotIn("alias-unexplained", {k[0] for k in found})
        self.assertNotIn("possible-alias", {k[0] for k in found})

    def test_owner_id_and_created_by_are_not_merged_silently(self):
        a = [entity("Doc", [{"name": "owner_id", "type": "int", "description": "the person who currently owns it"}])]
        b = [entity("Doc", [{"name": "created_by", "type": "int", "description": "the author who first wrote it"}])]
        found, _ = self.run_compat(a, b, aliases={"fields": {"created_by": {"to": "owner_id", "reason": "guess"}}})
        self.assertIn(("field-meaning", "doc.owner_id"), found)
        self.assertEqual(found[("field-meaning", "doc.owner_id")]["severity"], "high")

    def test_status_meanings_admins_and_deletion(self):
        a = [entity("Task", [{"name": "status", "type": "text", "enum": ["open", "closed"]},
                             {"name": "deleted_at", "type": "timestamp"}])]
        b = [entity("Task", [{"name": "status", "type": "text", "enum": ["todo", "done", "archived"]}],
                    deletion="hard")]
        found, _ = self.run_compat(a, b, A={"auth": {"roles": ["admin"], "role_permissions": {"admin": ["*"]}}},
                                   B={"auth": {"roles": ["admin"], "role_permissions": {"admin": ["tasks:edit"]}}})
        self.assertIn(("enum", "task.status"), found)
        self.assertIn(("role-meaning", "admin"), found)
        self.assertIn(("deletion-semantics", "task"), found)

    def test_dates_currency_and_timezones(self):
        a = [entity("Order", [{"name": "placed_at", "type": "timestamp", "timezone": "UTC"},
                              {"name": "total", "type": "integer", "unit": "cents", "currency": "EUR"}])]
        b = [entity("Order", [{"name": "placed_at", "type": "integer", "description": "unix epoch seconds",
                               "timezone": "local"},
                              {"name": "total", "type": "decimal", "unit": "units", "currency": "USD"}])]
        found, report = self.run_compat(a, b)
        for key in (("field-type", "order.placed_at"), ("units", "order.placed_at.timezone"),
                    ("units", "order.total.currency"), ("units", "order.total.unit"), ("field-type", "order.total")):
            self.assertIn(key, found, key)
        mig = next(m for m in report["migrations"] if m["id"] == "migration:order")
        self.assertEqual(mig["risk"], "high")
        self.assertTrue(any("convert total to one currency" in c for c in mig["changes"]))

    def test_same_name_same_meaning_is_not_flagged(self):
        a = [entity("Task", [{"name": "title", "type": "text"}, {"name": "due", "type": "date"}],
                    description="a piece of work to do")]
        b = [entity("Task", [{"name": "title", "type": "text"}, {"name": "due", "type": "date"}],
                    description="a piece of work someone must do")]
        found, _ = self.run_compat(a, b)
        self.assertNotIn("entity-meaning", {k[0] for k in found})
        self.assertIn(("duplicate-entity", "task"), found)

    def test_same_name_different_meaning_needs_a_decision(self):
        a = [entity("Account", [{"name": "email", "type": "text"}, {"name": "password_hash", "type": "text"}],
                    "uuid", description="a person who signs in")]
        b = [entity("Account", [{"name": "balance", "type": "decimal"}, {"name": "iban", "type": "text"}],
                    "uuid", description="a ledger holding money")]
        found, _ = self.run_compat(a, b)
        c = found[("entity-meaning", "account")]
        self.assertTrue(c["needs_approval"])
        self.assertIn("ledger", c["detail"])
        self.assertIn("never merge", c["recommended"])


class SchemaConflictTest(CompatCase):
    """Test I: structures that cannot be merged as they are produce a plan with its risks, never a silent drop."""

    def test_keys_relations_constraints_and_policies(self):
        a = [entity("Project", []),
             entity("Tag", []),
             entity("Task", [{"name": "project_id", "type": "int"}, {"name": "code", "type": "text", "unique": True},
                             {"name": "assignee", "type": "text", "nullable": True},
                             {"name": "tag_id", "type": "int"}],
                    foreign_keys=[{"field": "project_id", "references": "Project.id", "on_delete": "cascade"},
                                  {"field": "tag_id", "references": "Tag.id"}])]
        b = [entity("Project", [], "uuid"),
             entity("Tag", [], "uuid"),
             entity("Task", [{"name": "project_id", "type": "uuid"}, {"name": "code", "type": "text", "unique": False},
                             {"name": "assignee", "type": "text", "required": True}], "uuid",
                    foreign_keys=[{"field": "project_id", "references": "projects(id)", "on_delete": "restrict"}]),
             entity("TaskTag", [{"name": "task_id", "type": "uuid"}, {"name": "tag_id", "type": "uuid"}], "uuid",
                    foreign_keys=[{"field": "task_id", "references": "tasks(id)"},
                                  {"field": "tag_id", "references": "tags(id)"}])]
        found, report = self.run_compat(a, b)
        for key in (("primary-key", "task"), ("primary-key", "project"), ("unique-constraint", "task.code"),
                    ("nullability", "task.assignee"), ("delete-policy", "task.project_id"),
                    ("cardinality", "tag-task"), ("field-type", "task.project_id")):
            self.assertIn(key, found, key)
        self.assertEqual(found[("primary-key", "task")]["severity"], "critical")
        mig = next(m for m in report["migrations"] if m["id"] == "migration:task")
        self.assertTrue(mig["destructive"])
        self.assertTrue(any("relation tag-task: keep every link" in c for c in
                            next(m for m in report["migrations"] if m["id"] in ("migration:tag", "migration:task"))
                            ["changes"]) or any("keep every link" in c for m in report["migrations"]
                                                for c in m["changes"]))
        self.assertTrue(any("find duplicate values" in c for c in mig["changes"]))

    def test_dropping_fields_in_the_design_is_never_silent(self):
        a = [entity("Note", [{"name": "body", "type": "text"}, {"name": "color", "type": "text"}])]
        b = [entity("Note", [{"name": "body", "type": "text"}])]
        arch = {"entities": [{"name": "Note", "merged_from": ["A:Note", "B:Note"],
                              "fields": [{"name": "id", "type": "int"}, {"name": "body", "type": "text"}]}]}
        found, report = self.run_compat(a, b, arch=arch)
        mig = next(m for m in report["migrations"] if m["id"] == "migration:note")
        self.assertIn("color", mig["data_loss"])
        self.assertTrue(mig["needs_approval"])

    def test_cli_writes_the_plan(self):
        ws = Workspace(apps=("A", "B"), format=3)
        self.addCleanup(ws.close)
        ws.set_source("A", source_json("A", entities=[entity("Item", [{"name": "status", "type": "text",
                                                                       "enum": ["a"]}])]))
        ws.set_source("B", source_json("B", entities=[entity("Item", [{"name": "status", "type": "text",
                                                                       "enum": ["b"]}], "uuid")]))
        r = run_script("check_compatibility.py", ws.mixer, "--all", "--write")
        self.assertEqual(r.returncode, 1, r.stdout)  # the critical key conflict blocks
        with open(os.path.join(ws.mixer, "compat", "compatibility-report.md")) as f:
            md = f.read()
        self.assertIn("database:enum:item.status", md)
        self.assertIn("## Migrations", md)


if __name__ == "__main__":
    unittest.main()
