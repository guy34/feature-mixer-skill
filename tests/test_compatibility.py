"""Compatibility analysis: database, API, authentication and application conflicts."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import Workspace, row, source_json  # noqa: E402

import check_compatibility as cc  # noqa: E402


def ev(app, n=1):
    return [f"{app}-E0{n}"]


def app_a():
    return source_json(
        "A", "TaskBoard",
        features=[{"id": "A-F01", "name": "Sign in", "description": "x", "evidence": ev("A"), "basis": "observed",
                   "confidence": "high"},
                  {"id": "A-F02", "name": "Tasks", "description": "x", "evidence": ev("A"), "basis": "observed",
                   "confidence": "high"},
                  {"id": "A-F03", "name": "Flat comments", "description": "x", "evidence": ev("A"),
                   "basis": "observed", "confidence": "high"}],
        entities=[
            {"name": "User", "primary_key": {"name": "id", "type": "uuid"},
             "fields": [{"name": "id", "type": "uuid"}, {"name": "email", "type": "text"},
                        {"name": "name", "type": "varchar(80)"}],
             "features": ["A-F01"], "evidence": ev("A"), "basis": "observed"},
            {"name": "Task", "primary_key": {"name": "id", "type": "uuid"},
             "fields": [{"name": "id", "type": "uuid"}, {"name": "title", "type": "text"},
                        {"name": "due", "type": "date"}, {"name": "owner_id", "type": "uuid"}],
             "foreign_keys": [{"field": "owner_id", "references": "User"}],
             "features": ["A-F02"], "evidence": ev("A"), "basis": "observed"},
            {"name": "Comment", "primary_key": {"name": "id", "type": "uuid"},
             "fields": [{"name": "body", "type": "text"}], "features": ["A-F03"], "evidence": ev("A"),
             "basis": "observed"},
        ],
        endpoints=[
            {"method": "GET", "path": "/api/users/{id}", "auth": "session", "response": {"id": "uuid", "name": "text"},
             "features": ["A-F01"], "evidence": ev("A"), "basis": "observed"},
            {"method": "PATCH", "path": "/api/tasks/:id", "auth": "session", "features": ["A-F02"],
             "evidence": ev("A"), "basis": "observed"},
        ],
        auth={"provider": "self", "methods": ["password"], "session": "cookie", "model": "rbac",
              "roles": ["owner", "member"], "evidence": ev("A")},
        routes=[{"path": "/settings"}],
        rules=[{"key": "session.idle_timeout_minutes", "value": 60, "evidence": ev("A")}],
        components=[{"name": "Button", "variants": ["primary", "ghost"]}],
        integrations=[{"name": "Slack", "evidence": ev("A")}],
    )


def app_b():
    return source_json(
        "B", "Approvals",
        features=[{"id": "B-F01", "name": "Approvals", "description": "x", "evidence": ev("B"), "basis": "observed",
                   "confidence": "high"}],
        entities=[
            {"name": "Person", "primary_key": {"name": "id", "type": "serial"},
             "fields": [{"name": "id", "type": "integer"}, {"name": "email", "type": "string"},
                        {"name": "full_name", "type": "text"}, {"name": "createdAt", "type": "timestamp"}],
             "features": ["B-F01"], "evidence": ev("B"), "basis": "observed"},
            {"name": "Ticket", "primary_key": {"name": "id", "type": "uuid"},
             "fields": [{"name": "id", "type": "uuid"}, {"name": "title", "type": "text"},
                        {"name": "due", "type": "timestamp"}, {"name": "person_id", "type": "uuid"}],
             "foreign_keys": [{"field": "person_id", "references": "Person"}],
             "features": ["B-F01"], "evidence": ev("B"), "basis": "observed"},
        ],
        endpoints=[
            {"method": "GET", "path": "/api/v1/users/<int:id>", "auth": "bearer",
             "response": {"id": "integer", "full_name": "text"}, "features": ["B-F01"], "evidence": ev("B"),
             "basis": "documented"},
            {"method": "PUT", "path": "/api/tasks/{taskId}", "auth": "bearer", "features": ["B-F01"],
             "evidence": ev("B"), "basis": "documented"},
        ],
        auth={"provider": "auth0", "methods": ["password", "google"], "session": "jwt-header", "model": "rbac",
              "roles": ["requester", "approver", "admin"], "evidence": ev("B")},
        routes=[{"path": "/Settings/"}],
        rules=[{"key": "session.idle_timeout_minutes", "value": 30, "evidence": ev("B")}],
        components=[{"name": "button", "variants": ["primary", "danger"]}],
        integrations=[{"name": "slack", "evidence": ev("B")}],
    )


class CompatibilityTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(apps=("A", "B"))
        self.ws.set_source("A", app_a())
        self.ws.set_source("B", app_b())
        self.ws.write_json("compat/aliases.json", {"entities": {"Person": "User", "Ticket": "Task"},
                                                   "fields": {"full_name": "name", "person_id": "owner_id"}})

    def tearDown(self):
        self.ws.close()

    def report(self, **kw):
        return cc.run(self.ws.mixer, **kw)

    def ids(self, rep=None):
        rep = rep or self.report()
        return {c["id"]: c for c in rep["conflicts"]}

    # database
    def test_primary_key_conflict_is_critical_and_blocks(self):
        found = self.ids()
        c = found["database:primary-key:user"]
        self.assertEqual(c["severity"], "critical")
        self.assertIn("A: uuid", c["detail"])
        self.assertIn("B: integer", c["detail"])
        r = self.ws.run("check_compatibility.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("block integration", r.stdout)

    def test_aliases_merge_entities_and_fields(self):
        found = self.ids()
        self.assertIn("database:duplicate-entity:task", found)
        self.assertIn("A:Task, B:Ticket", found["database:duplicate-entity:task"]["detail"])
        self.assertEqual(found["database:field-type:task.due"]["severity"], "high")
        self.assertNotIn("database:field-type:user.name", found)

    def test_foreign_key_type_mismatch(self):
        found = self.ids()
        c = found["database:foreign-key:B.Ticket.person_id"]
        self.assertIn("is uuid but Person's key is serial", c["detail"])

    def test_naming_style_and_migrations(self):
        rep = self.report()
        self.assertIn("database:naming-style:fields", self.ids(rep))
        mig = {m["id"]: m for m in rep["migrations"]}
        self.assertTrue(mig["migration:user"]["destructive"])
        self.assertTrue(mig["migration:task"]["destructive"])

    # api
    def test_api_contract_conflicts(self):
        found = self.ids()
        self.assertIn("api:duplicate-endpoint:GET /api/users/{}", found)
        contract = found["api:contract:GET /api/users/{} response"]
        self.assertEqual(contract["severity"], "high")
        self.assertIn("id: A uuid, B integer", contract["detail"])
        self.assertIn("api:endpoint-auth:GET /api/users/{}", found)
        self.assertIn("A: none, B: v1", found["api:api-version:GET /api/users/{}"]["detail"])
        self.assertIn("A: PATCH, B: PUT", found["api:method:/api/tasks/{}"]["detail"])

    # application
    def test_authentication_conflicts(self):
        found = self.ids()
        self.assertEqual(found["application:session:session"]["severity"], "high")
        self.assertEqual(found["application:auth-provider:provider"]["severity"], "high")
        self.assertEqual(found["application:auth-methods:methods"]["severity"], "medium")
        roles = found["application:roles:roles"]
        self.assertIn("A: member, owner", roles["detail"])
        self.assertNotIn("application:authorization-model:model", found)

    def test_routes_rules_components_integrations(self):
        found = self.ids()
        self.assertEqual(found["application:route:/settings"]["severity"], "high")
        self.assertIn("A: 60, B: 30", found["application:business-rule:session.idle_timeout_minutes"]["detail"])
        self.assertIn("application:component:button", found)
        self.assertIn("application:integration:slack", found)

    # resolutions and scope
    def test_resolutions_unblock_only_when_approved(self):
        crit = [c["id"] for c in self.report()["conflicts"] if c["severity"] == "critical"]
        self.ws.write_json("compat/resolutions.json",
                           {cid: {"decision": "uuid everywhere", "approved": False} for cid in crit})
        self.assertEqual(self.ws.run("check_compatibility.py").returncode, 1)
        self.assertEqual(self.ids()[crit[0]]["status"], "awaiting-approval")
        self.ws.write_json("compat/resolutions.json",
                           {cid: {"decision": "uuid everywhere", "approved": True, "by": "user"} for cid in crit})
        self.assertEqual(self.ws.run("check_compatibility.py").returncode, 0)
        self.assertEqual(self.ws.run("check_compatibility.py", "--strict").returncode, 1)

    def test_scope_follows_kept_features(self):
        self.ws.menu([row("M01", "Tasks", source_features="A-F02"),
                      row("M02", "Flat comments", source_features="A-F03", pick="drop",
                          implementation_strategy="reject"),
                      row("M03", "Approvals", source_app="B", evidence_refs="B-E01", source_features="B-F01")])
        rep = self.report()
        self.assertEqual(rep["scope"], "kept features only")
        found = self.ids(rep)
        self.assertNotIn("database:duplicate-entity:comment", found)
        self.assertNotIn("api:duplicate-endpoint:GET /api/users/{}", found)
        self.assertIn("database:duplicate-entity:task", found)
        self.assertEqual(found["database:duplicate-entity:task"]["menu_features"], ["M01", "M03"])
        self.assertIn("api:duplicate-endpoint:GET /api/users/{}", self.ids(self.report(use_all=True)))

    def test_manual_conflicts_join_the_report(self):
        self.ws.write_json("compat/manual-conflicts.json", [
            {"kind": "workflow", "subject": "task-closing", "apps": ["A", "B"], "severity": "critical",
             "detail": "A closes tasks freely; B needs an approval first", "solutions": ["Require approval"],
             "recommended": "Approval gates closing"}])
        found = self.ids()
        self.assertEqual(found["application:workflow:task-closing"]["severity"], "critical")

    def test_write_report_has_every_section(self):
        r = self.ws.run("check_compatibility.py", "--write")
        self.assertIn("wrote compat/compatibility-report.json", r.stdout)
        with open(os.path.join(self.ws.mixer, "compat", "compatibility-report.md")) as f:
            text = f.read()
        for label in ("**Conflict:**", "**Affected applications:**", "**Affected features:**", "**Severity:**",
                      "**Possible solutions:**", "**Recommended resolution:**", "**User approval required:**"):
            self.assertIn(label, text)
        with open(os.path.join(self.ws.mixer, "compat", "compatibility-report.json")) as f:
            self.assertGreater(len(json.load(f)["conflicts"]), 10)


if __name__ == "__main__":
    unittest.main()
