"""v2.1 intelligence: capabilities, merging, architecture styles, large repos, migrations, dependencies."""

import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import Workspace, row, run_script, source_json  # noqa: E402

import check_compatibility as cc  # noqa: E402
import check_dependencies as cd  # noqa: E402
import index_repo  # noqa: E402
import validate_artifacts as va  # noqa: E402
import validate_feature_menu as vfm  # noqa: E402
import validate_project as vp  # noqa: E402


def msgs(rep):
    return "\n".join(rep.errors + rep.warnings)


# --- capabilities ------------------------------------------------------------

class CapabilityTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(apps=("A",), format=3)
        self.addCleanup(self.ws.close)
        self.ws.scan("A")
        self.ws.menu([row("M01", "Sign in")])
        data = source_json("A")
        data["sources_used"] = [{"ref": "A-R01", "kind": "website", "location": "https://a.example"}]
        self.ws.set_source("A", data)
        self.ws.done_through("recon")

    def test_detects_environment_from_any_folder(self):
        with tempfile.TemporaryDirectory() as cwd:
            r = run_script("check_environment.py", "--mixer", self.ws.mixer, "--set", "browser=unavailable",
                           "no browser tool", cwd=cwd)
        self.assertEqual(r.returncode, 0, r.stdout)
        with open(os.path.join(self.ws.mixer, "capabilities.json")) as f:
            caps = json.load(f)["capabilities"]
        self.assertEqual(caps["terminal"]["status"], "available")
        self.assertEqual(caps["browser"], {"status": "unavailable", "detail": "no browser tool"})
        self.assertEqual(caps["web_fetch"]["status"], "not-checked")
        r = run_script("check_environment.py", "--mixer", self.ws.mixer)
        self.assertIn("browser              unavailable", r.stdout)  # earlier --set rows are kept
        bad = run_script("check_environment.py", "--mixer", self.ws.mixer, "--set", "browser=maybe", "x")
        self.assertEqual(bad.returncode, 2)

    def test_missing_capabilities_file(self):
        self.assertIn("missing capabilities.json", "\n".join(vp.run(self.ws.mixer)[0].errors))

    def test_website_claims_need_a_browser_or_fetch(self):
        self.ws.capabilities(browser="unavailable", web_fetch="not-needed")
        errs = "\n".join(vp.run(self.ws.mixer)[0].errors)
        self.assertIn("evidence comes from A-R01 (website), but the session could not read it", errs)
        self.ws.capabilities(browser="unavailable", web_fetch="available")
        self.assertTrue(vp.run(self.ws.mixer)[0].ok)

    def test_terminal_unavailable_is_recorded_not_faked(self):
        self.ws.capabilities(terminal="unavailable", test_execution="unavailable", web_fetch="available")
        with open(os.path.join(self.ws.mixer, "capabilities.json")) as f:
            caps = json.load(f)["capabilities"]
        self.assertEqual(caps["test_execution"]["status"], "unavailable")
        self.assertTrue(vp.run(self.ws.mixer)[0].ok)  # recon needs no terminal; tests would fail to verify later

    def test_claude_rows_must_be_decided(self):
        self.ws.capabilities(web_fetch="available", repository_access="not-checked")
        self.assertIn("'repository_access' is still not-checked", "\n".join(vp.run(self.ws.mixer)[0].errors))

    def test_github_needs_repository_access(self):
        data = source_json("A")
        data["sources_used"] = [{"ref": "A-R01", "kind": "github", "location": "https://github.com/x/y"}]
        self.ws.set_source("A", data)
        self.ws.capabilities()
        self.assertIn("(github), but the session could not read it", "\n".join(vp.run(self.ws.mixer)[0].errors))


# --- feature merging -----------------------------------------------------------

class MergeTypesTest(unittest.TestCase):
    def errors(self, rows):
        return vfm.validate(rows, list(rows[0]) + ["merge_type"]).errors

    def test_synonyms_are_accepted(self):
        rows = [row("M01", "Roles", merge_type="conflicting", conflicts_with="M02", implementation_strategy="rebuild"),
                row("M02", "Open links", merge_type="conflicting", conflicts_with="M01", pick="drop",
                    implementation_strategy="reject"),
                row("M03", "Dashboard", merge_type="independent")]
        self.assertEqual(self.errors(rows), [])

    def test_separate_features(self):
        rows = [row("M01", "Public status page", merge_group="incidents", merge_type="separate",
                    integration_notes="public, read-only"),
                row("M02", "Internal incident log", merge_group="incidents", merge_type="separate",
                    implementation_strategy="combine")]
        errs = "\n".join(self.errors(rows))
        self.assertIn("M02 (Internal incident log): is separate (deliberately kept apart)", errs)
        self.assertIn("is separate but integration_notes does not say where its boundary is", errs)

    def test_improve_needs_a_note(self):
        errs = "\n".join(self.errors([row("M01", "Password reset", implementation_strategy="improve")]))
        self.assertIn("strategy improve needs integration_notes", errs)
        self.assertEqual(self.errors([row("M01", "Password reset", implementation_strategy="improve",
                                          integration_notes="add expiry")]), [])


class MergePlanTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(apps=("A", "B"), format=3)
        self.addCleanup(self.ws.close)
        self.ws.menu([
            row("M01", "In-app", merge_group="notify", merge_type="complementary", implementation_strategy="combine",
                source_features="A-F01"),
            row("M02", "Email", merge_group="notify", merge_type="complementary", implementation_strategy="combine",
                source_app="B", evidence_refs="B-E01", source_features="B-F01"),
            row("M03", "Status page", merge_group="incidents", merge_type="separate", integration_notes="public"),
            row("M04", "Incident log", merge_group="incidents", merge_type="separate", integration_notes="internal",
                depends_on="M01"),
        ])
        self.plan = {"unified_features": [
            {"id": "U01", "name": "Notifications", "menu_ids": ["M01", "M02"], "source_features": ["A-F01", "B-F01"],
             "evidence": ["A-E01", "B-E01"], "merge_type": "complementary", "rationale": "channels",
             "behaviour": "one engine", "depends_on": [], "compatibility": "compatible", "validation": "untested"},
            {"id": "U02", "name": "Status page", "menu_ids": ["M03"], "source_features": [], "evidence": ["A-E01"],
             "merge_type": "separate", "rationale": "public", "behaviour": "read only", "depends_on": [],
             "compatibility": "compatible", "validation": "untested"},
            {"id": "U03", "name": "Incident log", "menu_ids": ["M04"], "source_features": [], "evidence": ["A-E01"],
             "merge_type": "separate", "rationale": "internal", "behaviour": "log", "depends_on": ["U01"],
             "compatibility": "compatible", "validation": "untested"}]}

    def check(self, plan=None, status=None):
        self.ws.write_json("merge-plan.json", plan or self.plan)
        return va.check_merge_plan(self.ws.mixer, {"M01", "M02", "M03", "M04"}, True, status)

    def test_valid_plan(self):
        rep = self.check()
        self.assertTrue(rep.ok, rep.errors)

    def test_duplicate_functionality_and_double_build(self):
        p = copy.deepcopy(self.plan)
        p["unified_features"][2]["name"] = "notifications"
        p["unified_features"][2]["menu_ids"] = ["M04", "M01"]
        errs = "\n".join(self.check(p).errors)
        self.assertIn("two unified features are both called 'notifications': duplicate functionality", errs)
        self.assertIn("M01 appears in U01, U03; it must be built once", errs)

    def test_groups_follow_their_merge_type(self):
        p = copy.deepcopy(self.plan)
        p["unified_features"][0]["menu_ids"] = ["M01"]
        p["unified_features"].append(dict(p["unified_features"][0], id="U04", name="Email", menu_ids=["M02"],
                                          evidence=["B-E01"], source_features=["B-F01"]))
        p["unified_features"][1]["menu_ids"] = ["M03", "M04"]
        del p["unified_features"][2]
        errs = "\n".join(self.check(p).errors)
        self.assertIn("group 'notify' is complementary but its kept features are split across U01, U04", errs)
        self.assertIn("group 'incidents' is separate, so each kept feature needs its own unified feature", errs)

    def test_missing_kept_and_evidence_from_elsewhere(self):
        p = copy.deepcopy(self.plan)
        del p["unified_features"][1]
        p["unified_features"][0]["evidence"] = ["A-E01", "B-E01", "C-E09"]
        errs = "\n".join(self.check(p).errors)
        self.assertIn("kept feature M03 is not in any unified feature", errs)
        self.assertIn("U01 cites evidence C-E09 that its menu rows do not", errs)

    def test_validation_must_match_tests(self):
        p = copy.deepcopy(self.plan)
        p["unified_features"][0]["validation"] = "verified"
        status = {"M01": "verified", "M02": "failed", "M03": "verified", "M04": "verified"}
        errs = "\n".join(self.check(p, status).errors)
        self.assertIn("U01 says validation 'verified' but the verified test results say 'failed'", errs)

    def test_dependencies_between_unified_features(self):
        p = copy.deepcopy(self.plan)
        p["unified_features"][2]["depends_on"] = []
        p["unified_features"][0]["depends_on"] = ["U09"]
        rep = self.check(p)
        self.assertIn("U01 depends on unknown unified feature U09", "\n".join(rep.errors))
        self.assertIn("U03 should depend on U01 (M04 needs M01)", "\n".join(rep.warnings))


# --- architecture styles -------------------------------------------------------

class ArchitectureStyleTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(apps=("A",), format=3)
        self.addCleanup(self.ws.close)
        self.ws.menu([row("M01", "Sign in"), row("M02", "Orders")])
        d = os.path.join(self.ws.mixer, "design")
        os.makedirs(d)
        for name, sections in (("prd.md", va.PRD_SECTIONS), ("architecture.md", va.ARCH_SECTIONS)):
            with open(os.path.join(d, name), "w") as f:
                f.write("# Doc\n\n" + "\n\n".join(sections) + "\n")
        self.ws.write_json("merge-plan.json", {"unified_features": [
            {"id": "U01", "name": "Sign in", "menu_ids": ["M01"], "source_features": [], "evidence": ["A-E01"],
             "merge_type": "unique", "rationale": "x", "behaviour": "x", "depends_on": [],
             "compatibility": "compatible", "validation": "untested"},
            {"id": "U02", "name": "Orders", "menu_ids": ["M02"], "source_features": [], "evidence": ["A-E01"],
             "merge_type": "unique", "rationale": "x", "behaviour": "x", "depends_on": [],
             "compatibility": "compatible", "validation": "untested"}]})
        self.arch = {
            "stack": {"reasons": {"x": "y"}},
            "modules": [{"name": "accounts", "responsibility": "users", "features": ["M01"], "depends_on": [],
                         "owns_entities": ["User"]},
                        {"name": "orders", "responsibility": "orders", "features": ["M02"], "depends_on": ["accounts"],
                         "owns_entities": ["Order"]}],
            "entities": [], "auth": {"method": "password", "session": "cookie", "roles": ["member"]}, "api": [],
            "slices": [{"id": "V1", "name": "all", "features": ["M01", "M02"], "status": "done"}], "decisions": [],
            "style": {"selected": "modular-monolith", "drivers": ["one team"], "reason": "simplest",
                      "alternatives": [{"style": "microservices", "fit": "poor", "reason": "ops cost"},
                                       {"style": "event-driven", "fit": "partial", "reason": "low volume"}]},
        }

    def check(self, strict=True):
        self.ws.write_json("design/architecture.json", self.arch)
        return va.check_design(self.ws.mixer, {"M01", "M02"}, strict)

    def test_monolith_is_valid(self):
        self.assertTrue(self.check().ok, self.check().errors)

    def test_style_required_with_alternatives(self):
        del self.arch["style"]
        self.assertIn("has no 'style'", "\n".join(self.check().errors))
        self.assertIn("has no 'style'", "\n".join(self.check(strict=False).warnings))
        self.arch["style"] = {"selected": "microservices", "drivers": ["x"], "reason": "x",
                              "alternatives": [{"style": "microservices", "fit": "good", "reason": "x"}]}
        errs = "\n".join(self.check().errors)
        self.assertIn("must compare at least two other architecture styles", errs)
        self.assertIn("lists the selected style 'microservices' again", errs)

    def test_microservices_rules(self):
        self.arch["style"]["selected"] = "microservices"
        self.arch["style"]["alternatives"] = [{"style": "modular-monolith", "fit": "partial", "reason": "x"},
                                              {"style": "hybrid", "fit": "partial", "reason": "x"}]
        self.arch["modules"][1]["owns_entities"] = ["Order", "User"]
        errs = "\n".join(self.check().errors)
        self.assertIn("microservices needs a service for every module; missing: accounts, orders", errs)
        self.assertIn("entity User is owned by several modules (accounts, orders)", errs)
        self.arch["modules"][0]["service"] = "identity"
        self.arch["modules"][1]["service"] = "identity"
        self.arch["modules"][1]["owns_entities"] = ["Order"]
        self.assertIn("with fewer than two services is a monolith", "\n".join(self.check().errors))
        self.arch["modules"][1]["service"] = "ordering"
        self.assertTrue(self.check().ok, self.check().errors)

    def test_event_driven_rules(self):
        self.arch["style"]["selected"] = "event-driven"
        self.arch["style"]["alternatives"] = [{"style": "modular-monolith", "fit": "good", "reason": "x"},
                                              {"style": "microservices", "fit": "poor", "reason": "x"}]
        self.assertIn("needs an 'events' list", "\n".join(self.check().errors))
        self.arch["events"] = [{"name": "order.placed", "producer": "orders", "consumers": ["billing"]}]
        self.assertIn("event order.placed names unknown module 'billing'", "\n".join(self.check().errors))
        self.arch["events"][0]["consumers"] = ["accounts"]
        self.assertTrue(self.check().ok)


# --- large repositories --------------------------------------------------------

class LargeRepoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "shop")
        files = {
            "src/orders/service.py": "from src.payments import client\nimport requests\n",
            "src/orders/__init__.py": "",
            "src/payments/client.py": "import stripe\nimport json\n",
            "src/payments/__init__.py": "",
            "web/app.js": "import x from './util';\nconst axios = require('axios');\nimport('@scope/pkg/sub')\n",
            "web/util.js": "export default 1\n",
            "web/dist/bundle.js": "x",
            "web/vendor.min.js": "x",
            "README.md": "# Shop\n",
            "node_modules/axios/index.js": "x",
        }
        for i in range(300):
            files[f"src/generated/m{i}.py"] = f"VALUE = {i}\n"
        for rel, text in files.items():
            path = os.path.join(self.repo, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
        self.index = index_repo.build(self.repo)

    def test_index_modules_and_imports(self):
        mods = self.index["modules"]
        self.assertEqual(sorted(mods), ["(root)", "src/generated", "src/orders", "src/payments", "web"])
        self.assertEqual(mods["src/generated"]["files"], 300)
        self.assertEqual(mods["src/orders"]["depends_on"], ["src/payments"])
        self.assertIn("requests", mods["src/orders"]["external"])
        self.assertEqual(sorted(mods["web"]["external"]), ["@scope/pkg", "axios"])
        self.assertIn("node_modules", self.index["skipped"])
        self.assertIn("web/dist", self.index["skipped"])
        minified = next(f for f in self.index["files"] if f["path"] == "web/vendor.min.js")
        self.assertTrue(minified["generated"])

    def make_ws(self, coverage, analysed, summaries=()):
        ws = Workspace(apps=("A",), format=3)
        self.addCleanup(ws.close)
        data = source_json("A", coverage=coverage, unknowns=["generated module not read"] if coverage == "partial" else [])
        data["sources_used"][0]["location"] = "src-repo"
        data["evidence"][0]["locator"] = "src-repo/src/orders/service.py:1"
        data["coverage_detail"] = {"index": "index.json", "modules_analysed": analysed,
                                   "modules_skipped": [{"module": "(root)", "reason": "README only"}]}
        ws.set_source("A", data)
        folder = ws.source_folder("A")
        with open(os.path.join(folder, "index.json"), "w") as f:
            json.dump(self.index, f)
        os.makedirs(os.path.join(folder, "summaries"))
        for s in summaries:
            open(os.path.join(folder, "summaries", s), "w").close()
        return ws, folder

    def test_complete_coverage_needs_every_module(self):
        ws, folder = self.make_ws("complete", ["src/orders"], ["src__orders.md"])
        errs = "\n".join(va.check_source(folder, "A", strict=True).errors)
        self.assertIn("coverage is 'complete' but modules were not analysed: src/generated, src/payments, web", errs)
        ws, folder = self.make_ws("partial", ["src/orders"], ["src__orders.md"])
        rep = va.check_source(folder, "A", strict=True)
        self.assertTrue(rep.ok, rep.errors)
        self.assertIn("3 module(s) not analysed yet", msgs(rep))

    def test_summaries_and_index_paths(self):
        ws, folder = self.make_ws("partial", ["src/orders", "web"], ["src__orders.md"])
        data = source_json("A", coverage="partial", unknowns=["x"])
        data["sources_used"][0]["location"] = "src-repo"
        data["evidence"][0]["locator"] = "src-repo/src/orders/missing.py:3"
        data["coverage_detail"] = {"index": "index.json", "modules_analysed": ["src/orders", "web", "nope"]}
        ws.set_source("A", data)
        errs = "\n".join(va.check_source(folder, "A", strict=True).errors)
        self.assertIn("analysed module 'web' has no summaries/web.md", errs)
        self.assertIn("names module 'nope', which is not in the index", errs)
        self.assertIn("evidence A-E01 points at src/orders/missing.py, which is not in the index", errs)

    def test_incremental_reanalysis(self):
        src = source_json("A")
        src["sources_used"][0]["location"] = "repo"
        src["evidence"][0]["locator"] = "repo/src/payments/client.py:1"
        src_path = os.path.join(self.tmp.name, "source.json")
        with open(src_path, "w") as f:
            json.dump(src, f)
        first = os.path.join(self.tmp.name, "i1.json")
        r = run_script("index_repo.py", self.repo, "--out", first, "--source-json", src_path)
        self.assertEqual(r.returncode, 0, r.stdout)
        with open(first) as f:
            self.assertEqual(json.load(f)["feature_files"], {"A-F01": ["src/payments/client.py"]})
        with open(os.path.join(self.repo, "src/payments/client.py"), "a") as f:
            f.write("# changed\n")
        os.remove(os.path.join(self.repo, "web/util.js"))
        second = os.path.join(self.tmp.name, "i2.json")
        r = run_script("index_repo.py", self.repo, "--out", second, "--previous", first, "--source-json", src_path)
        self.assertEqual(r.returncode, 1)
        self.assertIn("re-analyse these features (their evidence changed): A-F01", r.stdout)
        with open(second) as f:
            idx = json.load(f)
        self.assertEqual(idx["changes"]["changed"], ["src/payments/client.py"])
        self.assertEqual(idx["changes"]["removed"], ["web/util.js"])

    def test_stale_features_block_validation(self):
        ws, folder = self.make_ws("partial", ["src/orders"], ["src__orders.md"])
        idx = dict(self.index, stale_features=["A-F01"])
        with open(os.path.join(folder, "index.json"), "w") as f:
            json.dump(idx, f)
        self.assertIn("must be re-analysed: A-F01", "\n".join(va.check_source(folder, "A", strict=True).errors))


# --- migrations and data loss ----------------------------------------------------

class MigrationRiskTest(unittest.TestCase):
    def test_dropped_and_narrowed_fields(self):
        a = source_json("A", entities=[{"name": "Order", "primary_key": {"name": "id", "type": "uuid"},
                                        "fields": [{"name": "id", "type": "uuid"}, {"name": "total", "type": "numeric"},
                                                   {"name": "placed_at", "type": "timestamp"},
                                                   {"name": "gift_note", "type": "text"}],
                                        "evidence": ["A-E01"], "basis": "observed"}])
        arch = {"entities": [{"name": "Order", "merged_from": ["A:Order"],
                              "fields": [{"name": "id", "type": "uuid"}, {"name": "total", "type": "integer"},
                                         {"name": "placed_at", "type": "date"}]}]}
        _, migrations = cc.analyse({"A": a}, arch=arch)
        m = migrations[0]
        self.assertEqual((m["id"], m["risk"], m["destructive"]), ("migration:order", "high", True))
        self.assertEqual(m["data_loss"], ["gift_note", "placed_at", "total"])
        self.assertIn("A.Order fields not kept in Order: gift_note", m["changes"])

    def test_widening_is_low_risk(self):
        a = source_json("A", entities=[{"name": "Tag", "fields": [{"name": "code", "type": "integer"}],
                                        "evidence": ["A-E01"], "basis": "observed"}])
        arch = {"entities": [{"name": "Tag", "merged_from": ["A:Tag"], "fields": [{"name": "code", "type": "text"}]}]}
        _, migrations = cc.analyse({"A": a}, arch=arch)
        self.assertEqual((migrations[0]["risk"], migrations[0]["destructive"]), ("low", False))

    def test_renamed_field_is_not_lost(self):
        a = source_json("A", entities=[{"name": "User", "fields": [{"name": "full_name", "type": "text"}],
                                        "evidence": ["A-E01"], "basis": "observed"}])
        arch = {"entities": [{"name": "User", "merged_from": ["A:User"],
                              "fields": [{"name": "name", "type": "text", "from": ["A:User.full_name"]}]}]}
        _, migrations = cc.analyse({"A": a}, arch=arch)
        self.assertEqual(migrations[0]["data_loss"], [])


# --- dependency intelligence ------------------------------------------------------

class DependencyIntelligenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, data):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_audit_formats_are_confirmed(self):
        npm = self.write("npm.json", {"vulnerabilities": {"lodash": {"severity": "high", "via": [
            {"source": 1065, "url": "https://github.com/advisories/GHSA-x"}]}}})
        pip = self.write("pip.json", {"dependencies": [{"name": "flask", "version": "0.12",
                                                         "vulns": [{"id": "PYSEC-2018-66"}]}]})
        osv = self.write("osv.json", {"results": [{"packages": [{"package": {"name": "requests"},
                                                                 "vulnerabilities": [{"id": "GHSA-y",
                                                                                      "database_specific": {"severity": "MODERATE"}}]}]}]})
        found = cd.parse_audit(npm, "A") + cd.parse_audit(pip, "B") + cd.parse_audit(osv, "C")
        self.assertEqual([(v["package"], v["tool"], v["status"]) for v in found],
                         [("lodash", "npm audit", "confirmed"), ("flask", "pip-audit", "confirmed"),
                          ("requests", "osv-scanner", "confirmed")])
        conflicts = {c["subject"]: c["severity"] for c in cd.vulnerability_conflicts(found)}
        self.assertEqual(conflicts, {"A:lodash": "high", "B:flask": "medium", "C:requests": "medium"})
        with self.assertRaises(ValueError):
            cd.parse_audit(self.write("x.json", {"hello": 1}), "A")

    def test_unverified_warnings(self):
        stacks = {"A": {"packages": {"left-pad": "*", "mylib": "git+https://x/y.git", "react": "^18.2.0"},
                        "runtimes": {}}}
        warnings = cd.unverified_warnings(stacks)
        self.assertEqual([(w["package"], w["status"]) for w in warnings],
                         [("left-pad", "unverified"), ("mylib", "unverified")])

    def test_necessity_analysis(self):
        ws = Workspace(apps=("A",), format=3)
        self.addCleanup(ws.close)
        folder = ws.source_folder("A")
        index = {"files": [{"path": "a.py", "language": "python"}, {"path": "b.py", "language": "python"},
                           {"path": "c.js", "language": "javascript"}],
                 "external_imports": {"requests": ["a.py"], "yaml": ["b.py"], "json": ["a.py"], "fs": ["c.js"],
                                      "stripe": ["b.py"]},
                 "feature_files": {"A-F01": ["a.py"], "A-F02": ["b.py"]}}
        with open(os.path.join(folder, "index.json"), "w") as f:
            json.dump(index, f)
        stacks = {"A": {"packages": {"requests": "2.31", "PyYAML": "6.0", "flask": "3.0", "pytest": "8"},
                        "runtimes": {}}}
        n = cd.necessity(ws.mixer, stacks, kept_features={"A-F01"})["A"]
        # a v2.1 index has no import coverage, so v2.2 will not call anything unused from it
        self.assertEqual(n["possibly_unused"], [])
        self.assertEqual([x["package"] for x in n["not_determinable"]], ["flask"])
        self.assertIn("predates import coverage", n["not_determinable"][0]["why"])
        index["import_coverage"] = {"python": {"files": 2, "method": "parsed (ast)"},
                                    "javascript": {"files": 1, "method": "patterns"}}
        index["complete"] = True
        with open(os.path.join(folder, "index.json"), "w") as f:
            json.dump(index, f)
        n = cd.necessity(ws.mixer, stacks, kept_features={"A-F01"})["A"]
        self.assertEqual(n["possibly_unused"], ["flask"])
        self.assertEqual(n["undeclared"], ["stripe"])
        self.assertEqual(sorted(n["only_dropped_features"]), ["stripe", "yaml"])
        self.assertIn("unverified", n["status"])

    def test_audit_files_feed_compatibility(self):
        ws = Workspace(apps=("A",), format=3)
        self.addCleanup(ws.close)
        ws.write_json("compat/audit/A-npm.json", {"vulnerabilities": {"lodash": {"severity": "critical", "via": []}}})
        found = {c["id"]: c for c in cc.run(ws.mixer)["conflicts"]}
        self.assertEqual(found["dependency:vulnerability:A:lodash"]["severity"], "high")


if __name__ == "__main__":
    unittest.main()
