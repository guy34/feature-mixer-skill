"""Phase 5 (v2.2): large monorepos, contradictory documentation, closed sources, offline sessions."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import ROOT, Workspace, row, run_script, source_json  # noqa: E402

import check_dependencies as cd  # noqa: E402
import index_repo  # noqa: E402
import validate_artifacts as va  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
import generate_monorepo  # noqa: E402


class MonorepoTest(unittest.TestCase):
    """Test P."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="fm-mono-")
        cls.root = generate_monorepo.generate(os.path.join(cls.tmp, "mono"))
        tracemalloc.start()
        t0 = time.time()
        cls.idx = index_repo.build(cls.root)
        cls.seconds = time.time() - t0
        cls.peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        cls.files = {f["path"]: f for f in cls.idx["files"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_size_time_and_memory(self):
        self.assertGreater(self.idx["totals"]["files"], 1000)
        self.assertLess(self.seconds, 60)
        self.assertLess(self.peak, 200 * 1024 * 1024)
        self.assertTrue(self.idx["complete"])

    def test_unrelated_nested_repository_is_a_boundary(self):
        self.assertEqual(self.idx["nested_repositories"], ["third_party/other-app"])
        self.assertFalse(any(p.startswith("third_party/other-app/") for p in self.files))
        self.assertNotIn("left-pad", self.idx["external_imports"])

    def test_every_real_module_is_listed(self):
        mods = set(self.idx["modules"])
        for m in ("apps/web", "apps/admin", "services/api", "services/billing", "services/search", "packages/ui",
                  "packages/utils", "db", "legacy"):
            self.assertIn(m, mods)

    def test_generated_code_is_marked(self):
        self.assertTrue(self.files["apps/web/src/__generated__/graphql.ts"]["generated"])
        self.assertTrue(self.files["services/api/gen/client_0.py"]["generated"])
        self.assertFalse(self.files["services/api/app/routes/r0.py"]["generated"])

    def test_workspace_and_alias_imports_stay_inside(self):
        s0 = self.files["apps/web/src/screens/s0.tsx"]
        self.assertTrue(any(p.startswith("packages/ui/") for p in s0["imports"]))
        self.assertNotIn("@mono/ui", self.idx["external_imports"])
        self.assertIn("packages/ui", self.idx["modules"]["apps/web"]["depends_on"])
        self.assertEqual(self.files["apps/web/src/screens/s1.tsx"]["imports"], ["apps/web/src/lib/helper.ts"])

    def test_languages_and_coverage(self):
        cov = self.idx["import_coverage"]
        for lang in ("python", "typescript", "go", "rust", "java"):
            self.assertIn(lang, cov)
        self.assertIn("serde", self.idx["external_imports"])

    def test_dependencies_across_package_managers_and_the_internal_react_conflict(self):
        st = cd.scan_manifests(self.root)
        found = {(c["kind"], c["subject"]): c for c in cd.analyse({"A": st})}
        c = found[("version", "react")]
        self.assertIn("apps/web/package.json", c["detail"])
        self.assertIn("apps/admin/package.json", c["detail"])
        self.assertNotIn("^16.0.0", c["detail"], "the nested repository's manifest leaked in")
        for name in ("fastapi", "serde", "github.com/stripe/stripe-go/v76"):
            self.assertIn(name, st["packages"])
        self.assertEqual(set(st["runtimes"]) >= {"node", "python", "go", "rust"}, True)

    def test_progress_is_reported(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "feature-mixer", "scripts", "index_repo.py"), self.root,
                            "--out", os.path.join(self.tmp, "idx.json"), "--progress", "500"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("1000 files indexed", r.stderr)
        self.assertIn("separate repositories inside, not indexed: third_party/other-app", r.stdout)


def evidence(app, n, basis, source="R01", locator="x"):
    return {"id": f"{app}-E{n:02d}", "source": f"{app}-{source}", "basis": basis, "locator": locator, "summary": "s"}


class HonestyTest(unittest.TestCase):
    """Tests Q and R: observed, documented and inferred stay apart."""

    def ws(self, access="own-code", fmt=4):
        ws = Workspace(apps=("A",), format=fmt)
        self.addCleanup(ws.close)
        ws.project["sources"][0]["access"] = access
        ws.save()
        return ws

    def errors(self, ws, fmt=4):
        rep = va.check_all(ws.mixer)
        return "\n".join(rep.errors), "\n".join(rep.warnings)

    def test_documented_claims_are_not_observed(self):
        ws = self.ws()
        data = source_json("A", sources_used=[{"ref": "A-R01", "kind": "documentation", "location": "README.md"}],
                           evidence=[evidence("A", 1, "documented")],
                           features=[{"id": "A-F01", "name": "Export", "description": "d", "evidence": ["A-E01"],
                                      "basis": "observed", "confidence": "medium"}])
        ws.set_source("A", data)
        errs, _ = self.errors(ws)
        self.assertIn("claims 'observed' but its evidence is only documented", errs)
        ws.project["format"] = 3
        ws.save()
        errs, warns = self.errors(ws)
        self.assertNotIn("claims 'observed'", errs)
        self.assertIn("claims 'observed'", warns)

    def test_contradicted_documentation_is_not_a_feature(self):
        ws = self.ws()
        data = source_json("A", sources_used=[{"ref": "A-R01", "kind": "documentation", "location": "README.md"},
                                              {"ref": "A-R02", "kind": "local-directory", "location": "src"}],
                           evidence=[evidence("A", 1, "documented"), evidence("A", 2, "observed", "R02", "src/x.py:4")],
                           features=[{"id": "A-F01", "name": "CSV export", "description": "README says so",
                                      "evidence": ["A-E01"], "basis": "documented", "confidence": "low"}],
                           contradictions=[{"id": "A-C01", "documented": "A-E01", "observed": "A-E02",
                                            "summary": "README promises CSV export; the code only writes JSON"}])
        ws.set_source("A", data)
        errs, _ = self.errors(ws)
        self.assertIn("rests only on documentation the source's code contradicts", errs)
        self.assertIn("contradiction A-C01 has no resolution", errs)

    def test_closed_source_backend_was_not_inspected(self):
        ws = self.ws(access="closed")
        data = source_json("A", sources_used=[{"ref": "A-R01", "kind": "api-spec", "location": "openapi.yaml"},
                                              {"ref": "A-R02", "kind": "source-code", "location": "server"}],
                           evidence=[evidence("A", 1, "documented"), evidence("A", 2, "observed", "R02")],
                           features=[{"id": "A-F01", "name": "Orders API", "description": "d", "evidence": ["A-E01"],
                                      "basis": "documented", "confidence": "medium"}],
                           entities=[{"name": "Order", "fields": [], "basis": "observed", "evidence": ["A-E01"]}])
        ws.set_source("A", data)
        errs, _ = self.errors(ws)
        self.assertIn("closed source, but evidence A-E02 cites code", errs)
        self.assertIn("entity Order is marked observed without anything seen in the running product", errs)


class OfflineTest(unittest.TestCase):
    """Test S: no network, no registry, no false success."""

    def test_claims_needing_a_missing_capability_are_rejected(self):
        ws = Workspace(apps=("A",), format=4)
        self.addCleanup(ws.close)
        ws.capabilities(web_fetch="unavailable", browser="unavailable")
        ws.set_source("A", source_json("A", sources_used=[{"ref": "A-R01", "kind": "website",
                                                            "location": "https://app.example"}],
                                       evidence=[evidence("A", 1, "observed")]))
        errs = "\n".join(va.check_all(ws.mixer).errors)
        self.assertIn("the session could not read it", errs)

    def test_vulnerabilities_are_never_confirmed_without_an_audit_tool(self):
        ws = Workspace(apps=("A",), format=4)
        self.addCleanup(ws.close)
        src = os.path.join(ws.root, "src")
        os.makedirs(src)
        with open(os.path.join(src, "requirements.txt"), "w") as f:
            f.write("django==1.11\n")
        ws.project["sources"][0]["local_path"] = "src"
        ws.save()
        r = ws.run("check_dependencies.py", "--json")
        out = json.loads(r.stdout)
        self.assertEqual(out["intelligence"]["vulnerabilities"], [])
        plain = ws.run("check_dependencies.py")
        self.assertIn("vulnerabilities (confirmed by an audit tool): none supplied", plain.stdout)

    def test_a_failed_install_or_network_step_inside_the_tests_is_not_success(self):
        ws = Workspace(apps=("A",), format=4)
        self.addCleanup(ws.close)
        app = os.path.join(ws.root, "app")
        os.makedirs(os.path.join(app, "tests"))
        open(os.path.join(app, "tests", "__init__.py"), "w").close()
        with open(os.path.join(app, "tests", "test_net.py"), "w") as f:
            f.write("import unittest, urllib.request\nclass T(unittest.TestCase):\n    def test_fetch(self):\n"
                    "        urllib.request.urlopen('http://registry.invalid/simple/', timeout=2)\n")
        aid = ws.grant(app, unittest="tests")
        r = run_script("run_tests.py", "--mixer", ws.mixer, "--cwd", app, "--unittest", "tests", "--approval", aid)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("verdict failed", r.stdout)

    def test_scripts_make_no_network_calls(self):
        here = os.path.join(ROOT, "feature-mixer", "scripts")
        for name in os.listdir(here):
            if name.endswith(".py"):
                with open(os.path.join(here, name)) as f:
                    text = f.read()
                for mod in ("urllib.request", "http.client", "socket.create_connection", "requests", "ftplib"):
                    self.assertNotIn(f"import {mod}", text, f"{name} imports {mod}")

    def test_interrupted_phase_can_resume_from_a_checkpoint(self):
        ws = Workspace(apps=("A",), format=4)
        self.addCleanup(ws.close)
        ws.menu([row("M01", "Sign in")])
        ws.done_through("extraction")
        ws.project["phases"]["selection"] = {"status": "failed", "note": "interrupted"}
        ws.save()
        r = run_script("checkpoint.py", ws.mixer, "--list")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("CP2", r.stdout)


if __name__ == "__main__":
    unittest.main()
