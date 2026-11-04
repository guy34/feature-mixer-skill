"""Source reports, project phases, recovery, the example project, and the package itself."""

import json
import os
import py_compile
import re
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import EXAMPLE, ROOT, SCRIPTS, SKILL, Workspace, row, run_script, source_json  # noqa: E402

import validate_artifacts as va  # noqa: E402
import validate_project as vp  # noqa: E402


def messages(rep):
    return "\n".join(rep.errors + rep.warnings)


def kept_menu(apps):
    rows = []
    for i, a in enumerate(apps, start=1):
        rows.append(row(f"M{i:02d}", f"Feature from {a}", source_app=a, evidence_refs=f"{a}-E01",
                        source_features=f"{a}-F01", merge_group="sign-in" if len(apps) > 1 else "",
                        merge_type="identical" if len(apps) > 1 else "unique",
                        pick="keep" if i == 1 else "drop",
                        implementation_strategy="adapt" if i == 1 else "reject"))
    return rows


class SourceReportTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(apps=("A",))
        self.folder = self.ws.source_folder("A")

    def tearDown(self):
        self.ws.close()

    def check(self, data):
        self.ws.set_source("A", data)
        return va.check_source(self.folder, "A")

    def test_valid_source(self):
        self.assertTrue(va.check_source(self.folder, "A").ok)

    def test_partial_results_are_allowed_with_unknowns(self):
        rep = self.check(source_json("A", coverage="partial", unknowns=["How exports are scheduled"]))
        self.assertTrue(rep.ok, rep.errors)
        self.assertIn("partial coverage, 1 unknown(s) recorded", messages(rep))

    def test_partial_results_must_list_unknowns(self):
        rep = self.check(source_json("A", coverage="partial", unknowns=[]))
        self.assertIn("coverage is partial but unknowns is empty", messages(rep))

    def test_feature_without_evidence(self):
        data = source_json("A")
        data["features"][0]["evidence"] = []
        self.assertIn("A-F01 (Sign in) has no evidence", messages(self.check(data)))

    def test_missing_evidence_reference(self):
        data = source_json("A")
        data["features"][0]["evidence"] = ["A-E09"]
        self.assertIn("cites evidence A-E09, which does not exist", messages(self.check(data)))

    def test_assumptions_are_not_facts(self):
        data = source_json("A")
        data["features"][0].update(basis="inferred", confidence="high")
        self.assertIn("is inferred but marked high confidence", messages(self.check(data)))
        data = source_json("A")
        data["evidence"][0]["basis"] = "inferred"
        self.assertIn("claims 'observed' but its evidence is only inferred", messages(self.check(data)))

    def test_ids_carry_the_app_prefix(self):
        data = source_json("A")
        data["features"].append({"id": "B-F02", "name": "x", "description": "x", "evidence": ["A-E01"],
                                 "basis": "observed", "confidence": "high"})
        self.assertIn("feature id B-F02 does not start with A-", messages(self.check(data)))

    def test_workflow_steps_must_be_screens(self):
        data = source_json("A", screens=[{"id": "A-S01", "name": "Board", "evidence": ["A-E01"]}],
                           workflows=[{"id": "A-W01", "name": "Move a card", "steps": ["A-S01", "A-S02"],
                                       "evidence": ["A-E01"]}])
        self.assertIn("goes through A-S02, which is not a listed screen", messages(self.check(data)))

    def test_report_sections_and_schema(self):
        with open(os.path.join(self.folder, "report.md"), "w") as f:
            f.write("# Notes\n")
        data = source_json("A")
        del data["unknowns"]
        rep = self.check(data)
        self.assertIn("has no '## Evidence' section", messages(rep))
        self.assertIn("missing 'unknowns'", messages(rep))


class ProjectPhaseTest(unittest.TestCase):
    def make(self, apps):
        ws = Workspace(apps=apps)
        self.addCleanup(ws.close)
        ws.menu(kept_menu(apps))
        return ws

    def test_one_source_application(self):
        ws = self.make(("A",))
        ws.done_through("selection")
        r = ws.run("validate_project.py")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("selection is complete and valid", r.stdout)

    def test_two_independent_applications(self):
        ws = self.make(("A", "B"))
        ws.done_through("compatibility")
        r = ws.run("validate_project.py")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_three_or_more_applications(self):
        ws = self.make(("A", "B", "C", "D"))
        ws.done_through("selection")
        rep, _ = vp.run(ws.mixer)
        self.assertTrue(rep.ok, rep.errors)
        ws.project["sources"][3]["id"] = "A"
        ws.save()
        rep, _ = vp.run(ws.mixer)
        self.assertIn("app id A is used twice", messages(rep))

    def test_selection_needs_decisions_and_approval(self):
        ws = self.make(("A", "B"))
        rows = kept_menu(("A", "B"))
        rows[1]["pick"] = ""
        ws.menu(rows)
        ws.done_through("selection", approved=False)
        msg = messages(vp.run(ws.mixer)[0])
        self.assertIn("selection is done but not approved by the user", msg)
        self.assertIn("1 feature(s) still undecided: M02", msg)

    def test_menu_evidence_must_exist_in_reports(self):
        ws = self.make(("A", "B"))
        rows = kept_menu(("A", "B"))
        rows[0]["evidence_refs"] = "A-E07"
        rows[0]["source_features"] = "A-F09"
        ws.menu(rows)
        ws.done_through("extraction")
        msg = messages(vp.run(ws.mixer)[0])
        self.assertIn("cites evidence A-E07, which is not in any source report", msg)
        self.assertIn("maps to source feature A-F09, which no report contains", msg)

    def test_reuse_needs_a_licence_that_allows_it(self):
        ws = Workspace(apps=())
        self.addCleanup(ws.close)
        ws.add_source("A", code_reuse="not-allowed", access="closed")
        ws.save()
        ws.menu([row("M01", "Dashboard", implementation_strategy="adapt", source_features="A-F01")])
        ws.done_through("selection")
        self.assertIn("code_reuse there is 'not-allowed': use rebuild or combine", messages(vp.run(ws.mixer)[0]))

    def test_phases_run_in_order(self):
        ws = self.make(("A",))
        ws.phase("recon", "done")
        ws.phase("architecture", "in-progress")
        self.assertIn("architecture is in-progress but extraction is pending", messages(vp.run(ws.mixer)[0]))

    def test_failed_integration_recovery(self):
        ws = self.make(("A",))
        ws.done_through("architecture")
        ws.phase("implementation", "failed")
        r = ws.run("validate_project.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("implementation failed: fix it and rerun, or roll back to checkpoint CP5 "
                      "(architecture, git:mixer-cp5)", r.stdout)
        ws.phase("implementation", "rolled-back")
        msg = messages(vp.run(ws.mixer, "architecture")[0])
        self.assertIn("implementation was rolled back", msg)
        self.assertNotIn("implementation failed", msg)

    def test_deployment_never_automatic(self):
        ws = self.make(("A",))
        ws.done_through("integration")
        ws.phase("deployment", "in-progress")
        rep, _ = vp.run(ws.mixer, "deployment")
        self.assertIn("needs the user's explicit approval", messages(rep))

    def test_unresolved_critical_conflict_stops_compatibility(self):
        ws = self.make(("A", "B"))
        a, b = source_json("A"), source_json("B")
        a["entities"] = [{"name": "User", "primary_key": {"name": "id", "type": "uuid"}, "fields": [],
                          "evidence": ["A-E01"], "basis": "observed"}]
        b["entities"] = [{"name": "User", "primary_key": {"name": "id", "type": "integer"}, "fields": [],
                          "evidence": ["B-E01"], "basis": "observed"}]
        ws.set_source("A", a)
        ws.set_source("B", b)
        rows = kept_menu(("A", "B"))
        rows[1].update(pick="keep", merge_group="", merge_type="unique", implementation_strategy="adapt")
        ws.menu(rows)
        ws.done_through("compatibility")
        msg = messages(vp.run(ws.mixer)[0])
        self.assertIn("critical conflict database:primary-key:user is open", msg)
        self.assertIn("destructive migration migration:user needs explicit approval", msg)
        ws.write_json("compat/resolutions.json", {
            "database:primary-key:user": {"decision": "uuid", "approved": True},
            "migration:user": {"decision": "re-key B users", "approved": True}})
        rep, _ = vp.run(ws.mixer)
        self.assertTrue(rep.ok, rep.errors)


class DesignAndIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(apps=("A",))
        self.ws.menu([row("M01", "Sign in"), row("M02", "Tasks", depends_on="M01")])
        d = os.path.join(self.ws.mixer, "design")
        os.makedirs(d)
        for name, sections in (("prd.md", va.PRD_SECTIONS), ("architecture.md", va.ARCH_SECTIONS)):
            with open(os.path.join(d, name), "w") as f:
                f.write("# Doc\n\n" + "\n\n".join(sections) + "\n")
        self.arch = {
            "stack": {"backend": "Python", "reasons": {"backend": "team knows it"}},
            "modules": [{"name": "accounts", "responsibility": "users", "features": ["M01"], "depends_on": []},
                        {"name": "tasks", "responsibility": "tasks", "features": ["M02"], "depends_on": ["accounts"]}],
            "entities": [{"name": "User", "merged_from": ["A:User"]}],
            "auth": {"method": "password", "session": "cookie", "roles": ["member"]},
            "api": [{"method": "GET", "path": "/api/tasks", "module": "tasks"}],
            "slices": [{"id": "V1", "name": "core", "features": ["M01", "M02"], "status": "done"}],
            "decisions": [{"id": "D01", "decision": "Python", "reason": "team"}],
        }

    def tearDown(self):
        self.ws.close()

    def design(self):
        self.ws.write_json("design/architecture.json", self.arch)
        return va.check_design(self.ws.mixer, {"M01", "M02"})

    def test_valid_design(self):
        self.assertTrue(self.design().ok, self.design().errors)

    def test_design_problems(self):
        self.arch["modules"][0]["depends_on"] = ["tasks"]
        self.arch["modules"][1]["features"] = []
        self.arch["api"].append({"method": "GET", "path": "/api/tasks/", "module": "tasks"})
        self.arch["slices"][0]["features"] = ["M01"]
        msg = messages(self.design())
        self.assertIn("circular module dependency accounts -> tasks -> accounts", msg)
        self.assertIn("kept feature M02 is not assigned to any module", msg)
        self.assertIn("GET /api/tasks/ is defined twice", msg)
        self.assertIn("kept feature M02 is not in any slice", msg)

    def integration(self, tests):
        counts = {s: sum(t["status"] == s for t in tests) for s in ("pass", "fail", "skip")}
        self.ws.write_json("integration-report.json", {
            "app": "x", "command": "python3 -m unittest",
            "summary": {"total": len(tests), "passed": counts["pass"], "failed": counts["fail"],
                        "skipped": counts["skip"]},
            "tests": tests})
        with open(os.path.join(self.ws.mixer, "integration-report.md"), "w") as f:
            f.write("# Report\n\n" + "\n\n".join(va.INTEGRATION_SECTIONS) + "\n")
        return va.check_integration(self.ws.mixer, {"M01", "M02"})

    def test_every_kept_feature_needs_a_passing_test(self):
        rep = self.integration([
            {"name": "login", "features": ["M01"], "expected": "200", "actual": "200", "status": "pass"},
            {"name": "tasks", "features": ["M02"], "expected": "201", "actual": "500", "status": "fail",
             "error": "KeyError: owner"},
        ])
        msg = messages(rep)
        self.assertIn("failing test tasks (M02): KeyError: owner", msg)
        self.assertIn("kept feature M02 has no passing test, so it is not verified", msg)
        self.assertIn("has no recommended fix recorded", msg)

    def test_all_passing(self):
        rep = self.integration([
            {"name": "login", "features": ["M01"], "expected": "200", "actual": "200", "status": "pass"},
            {"name": "tasks", "features": ["M02"], "expected": "201", "actual": "201", "status": "pass"},
        ])
        self.assertTrue(rep.ok, rep.errors)


class ExampleProjectTest(unittest.TestCase):
    """The example in examples/team-hub: three apps through every phase but deployment."""

    def test_example_workspace_is_valid(self):
        r = run_script("validate_project.py", os.path.join(EXAMPLE, "mixer"))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("integration is complete and valid", r.stdout)

    def test_example_compatibility_is_clear(self):
        r = run_script("check_compatibility.py", os.path.join(EXAMPLE, "mixer"), "--strict")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_example_app_tests_pass(self):
        app = os.path.join(EXAMPLE, "app")
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                           cwd=app, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])


class StandaloneTest(unittest.TestCase):
    """Feature Mixer must work without Replica or any other skill."""

    def skill_files(self):
        for base, _, names in os.walk(SKILL):
            if "__pycache__" in base:
                continue
            for n in names:
                if n.endswith((".md", ".py", ".json", ".csv")):
                    yield os.path.join(base, n)

    def test_skill_never_mentions_replica(self):
        for path in self.skill_files():
            with open(path, encoding="utf-8") as f:
                self.assertFalse("replica" in f.read().lower(), f"{path} mentions Replica")

    def test_readme_and_manifests_require_nothing_else(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            readme = f.read().lower()
        for needle in ("replica-skill@", "/replica-", "install replica", "requires replica"):
            self.assertFalse(needle in readme, f"README still says '{needle}'")
        for name in ("plugin.json", "marketplace.json"):
            with open(os.path.join(ROOT, ".claude-plugin", name), encoding="utf-8") as f:
                self.assertFalse("replica" in f.read().lower(), f"{name} mentions Replica")

    @unittest.skipUnless(hasattr(sys, "stdlib_module_names"), "needs Python 3.10+ to list standard modules")
    def test_scripts_use_only_the_standard_library(self):
        allowed = set(sys.stdlib_module_names) | {
            n[:-3] for n in os.listdir(SCRIPTS) if n.endswith(".py")}
        for name in os.listdir(SCRIPTS):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(SCRIPTS, name), encoding="utf-8") as f:
                text = f.read()
            for mod in re.findall(r"^\s*(?:from|import)\s+([a-zA-Z_]\w*)", text, re.M):
                self.assertIn(mod, allowed, f"{name} imports {mod}")


class PackageStructureTest(unittest.TestCase):
    def load(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
            return json.load(f)

    def test_plugin_metadata(self):
        plugin = self.load(".claude-plugin", "plugin.json")
        market = self.load(".claude-plugin", "marketplace.json")
        with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
            top = re.search(r"^## (\d+\.\d+\.\d+)", f.read(), re.M).group(1)
        self.assertEqual(plugin["version"], top)
        self.assertEqual(plugin["name"], market["plugins"][0]["name"])
        self.assertEqual(plugin["license"], "MIT")
        self.assertTrue(os.path.isfile(os.path.join(ROOT, plugin["skills"], "feature-mixer", "SKILL.md")))
        self.assertIn("guy34", plugin["repository"])

    def test_skill_frontmatter(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        m = re.match(r"^---\nname: (.+)\ndescription: (.+)\n---\n", text)
        self.assertIsNotNone(m, "SKILL.md needs name and description frontmatter")
        self.assertEqual(m.group(1).strip(), "feature-mixer")
        self.assertLess(len(m.group(2)), 1024)

    def test_every_referenced_file_exists(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        for base, _, names in os.walk(os.path.join(SKILL, "engines")):
            for n in names:
                with open(os.path.join(base, n), encoding="utf-8") as f:
                    text += f.read()
        refs = set(re.findall(r"\b((?:engines|scripts|templates|schemas)/[\w.-]+\.(?:md|py|json|csv))", text))
        self.assertGreater(len(refs), 15)
        for ref in sorted(refs):
            self.assertTrue(os.path.isfile(os.path.join(SKILL, ref)), ref)

    def test_expected_layout(self):
        expected = [
            "SKILL.md",
            "engines/reconnaissance.md", "engines/feature-intelligence.md", "engines/compatibility-analysis.md",
            "engines/architecture-design.md", "engines/implementation.md", "engines/validation.md",
            "scripts/validate_project.py", "scripts/check_dependencies.py", "scripts/check_compatibility.py",
            "scripts/validate_feature_menu.py", "scripts/validate_artifacts.py", "scripts/check_menu.py",
            "schemas/project.schema.json", "schemas/source-report.schema.json", "schemas/feature.schema.json",
            "schemas/architecture.schema.json",
            "templates/source-report.md", "templates/integration-report.md", "templates/architecture.md",
            "templates/prd.md", "templates/mixer-log.md", "templates/feature-menu.csv",
        ]
        for rel in expected:
            self.assertTrue(os.path.isfile(os.path.join(SKILL, rel)), rel)

    def test_scripts_compile_and_schemas_parse(self):
        for name in os.listdir(SCRIPTS):
            if name.endswith(".py"):
                py_compile.compile(os.path.join(SCRIPTS, name), doraise=True)
        for name in os.listdir(os.path.join(SKILL, "schemas")):
            data = self.load("feature-mixer", "schemas", name)
            self.assertIn("$schema", data, name)


if __name__ == "__main__":
    unittest.main()
