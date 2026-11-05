"""Release quality and v2.0 regression: packaging, discovery, the frozen v2.0 workspace, preserved modes."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import EXAMPLE, ROOT, SKILL, Workspace, row, run_script  # noqa: E402

import validate_project as vp  # noqa: E402

V2_FIXTURE = os.path.join(ROOT, "tests", "fixtures", "v2_0_workspace", "mixer")
RELEASE = os.path.join(ROOT, "tools", "release_check.py")


class ReleaseCheckTest(unittest.TestCase):
    def test_release_check_passes(self):
        with tempfile.TemporaryDirectory() as cwd:
            r = subprocess.run([sys.executable, RELEASE, "--clean"], cwd=cwd, capture_output=True, text=True,
                               timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for name in ("caches", "versions", "discovery", "references", "scripts", "json", "install docs"):
            self.assertRegex(r.stdout, rf"PASS\s+{name}")
        self.assertRegex(r.stdout, r"(PASS|NOT RUN)\s+plugin CLI")

    def test_package_builds_clean_zips(self):
        with tempfile.TemporaryDirectory() as out:
            r = subprocess.run([sys.executable, RELEASE, "--clean", "--package", out], capture_output=True,
                               text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stdout)
            with zipfile.ZipFile(os.path.join(out, "feature-mixer-claude-ai.zip")) as z:
                names = z.namelist()
            self.assertIn("feature-mixer/SKILL.md", names)
            self.assertIn("feature-mixer/engines/security.md", names)
            self.assertFalse([n for n in names if "__pycache__" in n or n.endswith(".pyc")])
            with zipfile.ZipFile(os.path.join(out, "feature-mixer-skill.zip")) as z:
                full = z.namelist()
            self.assertIn("feature-mixer-skill/.claude-plugin/plugin.json", full)
            self.assertIn("feature-mixer-skill/tools/release_check.py", full)

    def test_installed_skill_works_outside_the_repo(self):
        """Copy only the skill folder (as a plain install would) and run its scripts from elsewhere."""
        with tempfile.TemporaryDirectory() as home:
            target = os.path.join(home, ".claude", "skills", "feature-mixer")
            import shutil
            shutil.copytree(SKILL, target, ignore=shutil.ignore_patterns("__pycache__"))
            r = subprocess.run([sys.executable, os.path.join(target, "scripts", "validate_project.py"),
                                os.path.join(EXAMPLE, "mixer")], cwd=home, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)


class V2RegressionTest(unittest.TestCase):
    """The v2.0 example workspace, frozen, must still validate under v2.1."""

    def test_v2_workspace_still_validates(self):
        r = run_script("validate_project.py", V2_FIXTURE)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("integration is complete and valid", r.stdout)
        for warning in ("missing capabilities.json", "no security-scan.json", "has no 'style'",
                        "missing merge-plan.json", "no execution evidence"):
            self.assertIn(warning, r.stdout)

    def test_v2_tools_still_answer(self):
        menu = os.path.join(V2_FIXTURE, "feature-menu.csv")
        self.assertEqual(run_script("check_menu.py", menu).returncode, 0)
        self.assertEqual(run_script("validate_feature_menu.py", menu).returncode, 0)
        self.assertEqual(run_script("check_compatibility.py", V2_FIXTURE, "--strict").returncode, 0)


class ExampleStrictTest(unittest.TestCase):
    def test_example_is_a_v22_workspace(self):
        with open(os.path.join(EXAMPLE, "mixer", "project.json")) as f:
            self.assertEqual(json.load(f)["format"], 4)
        r = run_script("verify_tests.py", os.path.join(EXAMPLE, "mixer"), "--no-write")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("features: verified 11", r.stdout)


class PreservedModesTest(unittest.TestCase):
    def test_modes_and_states(self):
        for mode in ("full", "plan", "auto-pick"):
            ws = Workspace(apps=("A",), format=3)
            self.addCleanup(ws.close)
            ws.project["mode"] = mode
            ws.save()
            rep, _ = vp.run(ws.mixer)
            self.assertFalse([e for e in rep.errors if "project.json" in e], mode)
        text = ""
        for rel in ("SKILL.md", os.path.join("engines", "feature-intelligence.md")):
            with open(os.path.join(SKILL, rel)) as f:
                text += f.read()
        for word in ("`full`", "`plan`", "`auto-pick`", "keep", "drop", "later", "skip"):
            self.assertIn(word, text)

    def test_plan_mode_stops_after_architecture(self):
        ws = Workspace(apps=("A",), format=3)
        self.addCleanup(ws.close)
        ws.project["mode"] = "plan"
        ws.capabilities()
        ws.scan("A")
        ws.menu([row("M01", "Sign in", source_features="A-F01")])
        ws.done_through("selection")
        rep, target = vp.run(ws.mixer)
        self.assertEqual(target, "selection")
        self.assertTrue(rep.ok, rep.errors)


if __name__ == "__main__":
    unittest.main()
