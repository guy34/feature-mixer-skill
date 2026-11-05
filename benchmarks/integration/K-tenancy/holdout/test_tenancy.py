import unittest
import tenancy as m


class TenancyHoldout(unittest.TestCase):
    def setUp(self):
        self.app = m.create_app()
        self.o1, self.o2 = self.app.create_org("North"), self.app.create_org("South")
        self.u1, self.u2 = self.app.add_user(self.o1, "ana"), self.app.add_user(self.o2, "bo")
        self.p1 = self.app.create_project(self.u1, "north-secret-plan")
        self.p2 = self.app.create_project(self.u2, "south-roadmap")
        self.r2 = self.app.add_resource(self.u2, self.p2, "south confidential budget")
        self.t = self.app.create_template("Kick-off")

    def test_projects_carry_their_org(self):
        self.assertEqual(self.app.get_project(self.u1, self.p1)["org_id"], self.o1)

    def test_lists_never_cross_tenants(self):
        self.assertEqual([p["id"] for p in self.app.list_projects(self.u1)], [self.p1])
        self.assertEqual(self.app.list_resources(self.u1), [])

    def test_direct_access_across_tenants_is_refused(self):
        with self.assertRaises(PermissionError):
            self.app.get_project(self.u1, self.p2)
        with self.assertRaises(PermissionError):
            self.app.add_resource(self.u1, self.p2, "sneaky")
        with self.assertRaises(PermissionError):
            self.app.list_resources(self.u1, self.p2)

    def test_search_does_not_leak(self):
        self.assertEqual(self.app.search(self.u1, "south"), [])
        self.assertTrue(self.app.search(self.u2, "south"))

    def test_shared_templates_are_visible_and_read_only(self):
        for u in (self.u1, self.u2):
            self.assertEqual([t["id"] for t in self.app.list_templates(u)], [self.t])
        with self.assertRaises(PermissionError):
            self.app.update_template(self.u1, self.t, "Hijacked")
