"""The benchmark tools: answer keys, the large-repo generator, and the scorer."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import EXAMPLE, ROOT  # noqa: E402

BENCH = os.path.join(ROOT, "benchmarks")
sys.path.insert(0, BENCH)
import generate_large  # noqa: E402
import score  # noqa: E402


def tree_hash(root):
    h = hashlib.sha256()
    for base, dirs, files in sorted(os.walk(root)):
        dirs.sort()
        for f in sorted(files):
            path = os.path.join(base, f)
            h.update(os.path.relpath(path, root).encode())
            with open(path, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()


class BenchmarkToolsTest(unittest.TestCase):
    def test_answer_keys_are_complete(self):
        scen = os.path.join(BENCH, "scenarios")
        names = sorted(os.listdir(scen))
        self.assertEqual(len(names), 6)
        for n in names:
            with open(os.path.join(scen, n, "ground-truth.json")) as f:
                gt = json.load(f)
            self.assertEqual(gt["scenario"], n)
            self.assertIn(gt["mode"], ("plan", "full"))
            self.assertTrue(gt["features"])
            self.assertTrue(os.path.exists(os.path.join(scen, n, "task.md")))
            keys = {g["key"] for g in gt["features"]}
            for g in gt.get("groups", []):
                self.assertTrue(set(g["members"]) <= keys, n)

    def test_generator_is_reproducible(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra, rb = generate_large.generate(a, 42), generate_large.generate(b, 42)
            self.assertEqual(tree_hash(ra), tree_hash(rb))
            count = sum(len(f) for _, _, f in os.walk(ra))
            self.assertGreaterEqual(count, 400)
            with tempfile.TemporaryDirectory() as c:
                self.assertNotEqual(tree_hash(generate_large.generate(c, 7)), tree_hash(ra))

    def test_scorer_on_the_example(self):
        gt_path = os.path.join(ROOT, "tests", "fixtures", "example-ground-truth.json")
        with open(gt_path) as f:
            gt = json.load(f)
        result = score.score(gt, os.path.join(EXAMPLE, "mixer"))
        self.assertEqual(result["feature_recall"], 1.0)
        self.assertEqual(result["merge_accuracy"], 1.0)
        self.assertEqual(result["compatibility_recall"], 1.0)
        self.assertEqual(result["honesty"], 1.0)
        self.assertEqual(result["integration_completeness"], 1.0)
        self.assertEqual(result["fabricated"], 0)
        self.assertEqual(result["validator_exit"], 0)

    def test_scorer_notices_fabrication_and_overclaiming(self):
        gt = {"scenario": "x", "mode": "plan", "fabrication": ["teleport"], "coverage": {"A": "partial"},
              "features": [{"key": "a", "app": "A", "any": ["login"]}], "groups": [], "conflicts": []}
        with tempfile.TemporaryDirectory() as tmp:
            mixer = os.path.join(tmp, "mixer")
            folder = os.path.join(mixer, "sources", "A-app")
            os.makedirs(folder)
            with open(os.path.join(mixer, "project.json"), "w") as f:
                json.dump({"name": "x", "format": 3, "mode": "plan", "sources": [
                    {"id": "A", "name": "A", "slug": "app", "access": "own-code", "code_reuse": "allowed",
                     "inputs": [{"kind": "local-directory", "location": "a"}]}], "phases": {}}, f)
            with open(os.path.join(folder, "source.json"), "w") as f:
                json.dump({"app": {"id": "A", "name": "A"}, "coverage": "complete", "unknowns": [],
                           "features": [{"id": "A-F01", "name": "Login", "description": "x"},
                                        {"id": "A-F02", "name": "Teleport users", "description": "x"}]}, f)
            result = score.score(gt, mixer)
        self.assertEqual(result["feature_recall"], 1.0)
        self.assertEqual(result["feature_precision"], 0.5)
        self.assertEqual(result["fabricated"], 1)
        self.assertLess(result["honesty"], 1.0)
        self.assertIn("A coverage complete, expected partial", result["details"]["honesty"])


if __name__ == "__main__":
    unittest.main()
