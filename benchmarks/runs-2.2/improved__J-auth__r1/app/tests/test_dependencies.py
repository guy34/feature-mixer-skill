import ast
import os
import sys
import unittest

from tests.helpers import APP_DIR

STDLIB = getattr(sys, "stdlib_module_names", None) or {
    "hashlib", "hmac", "os", "secrets", "threading", "time", "uuid", "importlib", "sys"}


class DependencyTests(unittest.TestCase):
    def test_standard_library_only(self):
        """features: M01, M02, M03, M04, M05
        expect: the unified package imports only the standard library and itself
        level: dependency"""
        pkg = os.path.join(APP_DIR, "unified")
        for name in sorted(os.listdir(pkg)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(pkg, name), encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        continue
                    mods = [node.module.split(".")[0]]
                else:
                    continue
                for m in mods:
                    self.assertIn(m, STDLIB, f"{name} imports non-stdlib module {m}")


if __name__ == "__main__":
    unittest.main()
