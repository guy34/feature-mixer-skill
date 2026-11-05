"""Phase 6 (v2.2): checks that back the workflow rules. Decisions cannot change silently, plan mode builds
nothing, a passing unit suite is not an end-to-end proof, and a feature from no source must be a user request."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import Workspace, row, run_script, temp_menu  # noqa: E402

import validate_feature_menu as vfm  # noqa: E402
import validate_project as vp  # noqa: E402


def errors(rep):
    return "\n".join(rep.errors)


class ChangedAfterApprovalTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(apps=("A",), format=4)
        self.addCleanup(self.ws.close)
        self.ws.menu([row("M01", "Sign in"), row("M02", "Export", pick="drop")])
        self.ws.write_json("merge-plan.json", {"unified_features": []})

    def approve(self, phase="selection"):
        r = run_script("approvals.py", "approve-phase", "--mixer", self.ws.mixer, "--phase", phase,
                       "--granted-by", "test-user", "--user-confirmed")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.ws.reload()

    def test_a_pick_changed_after_approval_is_caught(self):
        self.approve()
        self.assertEqual(errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)), "")
        self.ws.menu([row("M01", "Sign in"), row("M02", "Export", pick="keep")])  # the requirement changed
        self.assertIn("selection: changed after the user approved it",
                      errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)))
        self.approve()  # shown to the user and approved again
        self.assertEqual(errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)), "")

    def test_notes_and_wording_may_change_but_not_decisions(self):
        self.approve()
        self.ws.menu([row("M01", "Sign in (email)", notes="clarified"), row("M02", "Export", pick="drop")])
        self.assertEqual(errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)), "")

    def test_compatibility_and_architecture_decisions(self):
        self.ws.write_json("compat/resolutions.json", {"database:primary-key:user": {"decision": "uuid",
                                                                                     "approved": True}})
        self.approve("compatibility")
        self.ws.write_json("compat/resolutions.json", {"database:primary-key:user": {"decision": "integer",
                                                                                     "approved": True}})
        self.assertIn("compatibility: changed after the user approved it",
                      errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)))
        self.ws.write_json("design/architecture.json", {"style": {"selected": "modular-monolith"}})
        self.approve("architecture")
        self.ws.write_json("design/architecture.json", {"style": {"selected": "microservices"}})
        self.assertIn("architecture: changed after the user approved it",
                      errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)))

    def test_progress_updates_are_not_decision_changes(self):
        # Found by three 2.2.0 benchmark runs: marking slices done or features verified forced re-approvals.
        uf = {"id": "U01", "name": "Sign in", "menu_ids": ["M01"], "compatibility": "conflict",
              "validation": "untested", "behaviour": "email and password"}
        self.ws.write_json("merge-plan.json", {"unified_features": [dict(uf)]})
        self.ws.write_json("design/architecture.json", {"style": {"selected": "modular-monolith"},
                                                        "slices": [{"id": "V1", "status": "pending"}]})
        self.approve("selection")
        self.approve("architecture")
        self.ws.write_json("merge-plan.json", {"unified_features": [dict(uf, compatibility="resolved",
                                                                         validation="verified")]})
        self.ws.write_json("design/architecture.json", {"style": {"selected": "modular-monolith"},
                                                        "slices": [{"id": "V1", "status": "done"}]})
        self.assertEqual(errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)), "")
        self.ws.write_json("merge-plan.json", {"unified_features": [dict(uf, behaviour="magic link")]})
        self.assertIn("selection: changed after the user approved it",
                      errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)))

    def test_approvals_recorded_by_2_2_0_still_check_by_bytes(self):
        import approvals
        self.ws.write_json("design/architecture.json", {"slices": [{"id": "V1", "status": "pending"}]})
        self.approve("architecture")
        entry = self.ws.project["phases"]["architecture"]
        entry.pop("approved_fingerprint_method")
        entry["approved_fingerprint"] = approvals.phase_fingerprint(self.ws.mixer, "architecture", 1)
        self.ws.save()
        self.assertEqual(errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)), "")
        self.ws.write_json("design/architecture.json", {"slices": [{"id": "V1", "status": "done"}]})
        self.assertIn("architecture: changed after the user approved it",
                      errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)))

    def test_format_4_needs_a_recorded_approval_and_older_formats_do_not(self):
        self.ws.phase("selection", "done", approved=True)
        self.assertIn("approved without a record of what was approved",
                      errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)))
        self.ws.project["format"] = 3
        self.ws.save()
        self.assertEqual(errors(vp.check_approved_unchanged(self.ws.mixer, self.ws.project)), "")

    def test_approve_phase_needs_the_users_yes(self):
        r = run_script("approvals.py", "approve-phase", "--mixer", self.ws.mixer, "--phase", "selection",
                       "--granted-by", "x")
        self.assertEqual(r.returncode, 1)
        self.ws.reload()
        self.assertNotIn("selection", self.ws.project["phases"])
        with open(os.path.join(self.ws.mixer, "approval-log.jsonl")) if os.path.exists(
                os.path.join(self.ws.mixer, "approval-log.jsonl")) else open(os.devnull) as f:
            self.assertNotIn("phase-approved", f.read())


class PlanModeTest(unittest.TestCase):
    def test_plan_mode_cannot_claim_a_build(self):
        ws = Workspace(apps=("A",), format=4)
        self.addCleanup(ws.close)
        ws.project["mode"] = "plan"
        ws.project["phases"] = {"implementation": {"status": "done"}}
        ws.save()
        self.assertIn("plan mode, which builds nothing", errors(vp.check_approved_unchanged(ws.mixer, ws.project)))


class JourneyTest(unittest.TestCase):
    def report(self, ws, tests):
        ws.write_json("integration-report.json", {"app": "x", "command": "c", "summary": {}, "tests": tests})

    def test_unit_tests_alone_are_not_enough_in_format_4(self):
        ws = Workspace(apps=("A",), format=4)
        self.addCleanup(ws.close)
        self.report(ws, [{"name": "t1", "level": "unit", "status": "passed", "features": ["M01"]}])
        self.assertIn("no journey-level test", errors(vp.check_journeys(ws.mixer, ws.project)))
        self.report(ws, [{"name": "t2", "level": "journey", "status": "failed", "features": ["M01"]}])
        self.assertIn("no journey-level test passed", errors(vp.check_journeys(ws.mixer, ws.project)))
        self.report(ws, [{"name": "t3", "level": "journey", "status": "passed", "features": ["M01"]}])
        self.assertEqual(errors(vp.check_journeys(ws.mixer, ws.project)), "")
        ws.project["format"] = 3
        self.report(ws, [{"name": "t1", "level": "unit", "status": "passed", "features": ["M01"]}])
        self.assertEqual(errors(vp.check_journeys(ws.mixer, ws.project)), "")


class InventedFeatureTest(unittest.TestCase):
    def check(self, rows):
        path = temp_menu(rows)
        self.addCleanup(os.remove, path)
        header, loaded = vfm.load_menu(path)
        return errors(vfm.validate(loaded, header))

    def test_a_feature_from_no_source_must_be_a_user_request(self):
        errs = self.check([row("M01", "AI summaries", source_app="new", evidence_refs="")])
        self.assertIn("is invented", errs)
        errs = self.check([row("M01", "AI summaries", source_app="new", evidence_refs="",
                               notes="Requested by the user on 4 Nov; not in any source")])
        self.assertNotIn("is invented", errs)
        self.assertNotIn("has no evidence_refs", errs)

    def test_a_sourced_feature_still_needs_evidence(self):
        self.assertIn("has no evidence_refs", self.check([row("M01", "Sign in", evidence_refs="")]))


if __name__ == "__main__":
    unittest.main()


class RequestedFeatureMergePlanTest(unittest.TestCase):
    """Found by a 2.2 benchmark run: a user-requested feature has no evidence, and the merge plan must accept that."""

    def test_requested_feature_needs_no_evidence_but_others_do(self):
        import validate_artifacts as va
        ws = Workspace(apps=("A",), format=4)
        self.addCleanup(ws.close)
        ws.menu([row("M01", "Sign in"), row("M02", "AI summaries", source_app="new", evidence_refs="",
                                             notes="Requested by the user")])
        base = {"name": "x", "source_features": [], "merge_type": "unique", "rationale": "r", "behaviour": "b",
                "depends_on": [], "compatibility": "compatible", "validation": "untested"}
        ws.write_json("merge-plan.json", {"unified_features": [
            dict(base, id="U01", menu_ids=["M01"], evidence=["A-E01"], source_features=["A-F01"]),
            dict(base, id="U02", menu_ids=["M02"], evidence=[])]})
        errs = "\n".join(va.check_merge_plan(ws.mixer, {"M01", "M02"}).errors)
        self.assertNotIn("U02 has no evidence", errs)
        ws.write_json("merge-plan.json", {"unified_features": [
            dict(base, id="U01", menu_ids=["M01"], evidence=[], source_features=["A-F01"]),
            dict(base, id="U02", menu_ids=["M02"], evidence=[])]})
        self.assertIn("U01 has no evidence", "\n".join(va.check_merge_plan(ws.mixer, {"M01", "M02"}).errors))
