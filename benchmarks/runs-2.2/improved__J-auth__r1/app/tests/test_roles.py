import unittest

from tests import helpers  # noqa: F401  (puts app/ on sys.path)
from unified import roles
from unified.identity import create_app, map_source_role


class RoleMappingTests(unittest.TestCase):
    def test_map_source_role(self):
        """features: M04
        acceptance: AC08
        expect: A user->editor, B member->viewer, C roles unchanged; unknown roles and apps raise KeyError
        level: unit"""
        app = create_app()
        self.assertEqual(app.map_source_role("A", "user"), "editor")
        self.assertEqual(app.map_source_role("B", "member"), "viewer")
        for r in ("viewer", "editor", "admin"):
            self.assertEqual(app.map_source_role("C", r), r)
        self.assertEqual(app.map_source_role("passbook", "user"), "editor")
        self.assertEqual(app.map_source_role("Linkup", "member"), "viewer")
        self.assertEqual(map_source_role("roster", "admin"), "admin")
        for bad in (("A", "admin"), ("A", "member"), ("B", "user"), ("B", "admin"), ("C", "user"),
                    ("C", "owner"), ("Z", "user"), ("A", ""), ("C", None)):
            with self.assertRaises(KeyError, msg=bad):
                app.map_source_role(*bad)

    def test_no_source_role_maps_to_admin_except_roster_admin(self):
        """features: M04
        expect: only C's admin becomes admin; no source role is escalated
        level: unit"""
        for app_id, mapping in roles.ROLE_MAPPING.items():
            for src, dst in mapping.items():
                if dst == "admin":
                    self.assertEqual((app_id, src), ("C", "admin"))

    def test_permission_check(self):
        """features: M04
        expect: viewer reads; editor reads and writes; only admin manages roles; unknown roles get nothing
        level: unit"""
        self.assertTrue(roles.can("viewer", "read"))
        self.assertFalse(roles.can("viewer", "write"))
        self.assertTrue(roles.can("editor", "write"))
        self.assertFalse(roles.can("editor", "manage_roles"))
        self.assertTrue(roles.can("admin", "manage_roles"))
        self.assertFalse(roles.can("superuser", "read"))
        self.assertFalse(roles.can(None, "read"))


if __name__ == "__main__":
    unittest.main()
