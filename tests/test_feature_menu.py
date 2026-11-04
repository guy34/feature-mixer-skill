"""Feature menu validation: the seven v1 tests, kept as they were, plus v2 checks."""

import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import SCRIPTS, SKILL, TEMPLATES, row, run_script, temp_menu

import check_menu  # noqa: E402
import mixerlib  # noqa: E402
import validate_feature_menu as vfm  # noqa: E402

TOOL = os.path.join(SCRIPTS, "check_menu.py")
EXAMPLE = os.path.join(TEMPLATES, "feature-menu.csv")

HEADER = ["id", "feature", "area", "source_app", "priority", "complexity",
          "depends_on", "conflicts_with", "pick", "notes"]


# --- v1 tests (unchanged apart from the new paths) ---------------------------

def write_menu(rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=HEADER)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in HEADER})
    f.close()
    return f.name


def run(path):
    import subprocess
    return subprocess.run([sys.executable, TOOL, path], capture_output=True, text=True)


class CheckMenuTest(unittest.TestCase):
    def test_consistent_picks_pass(self):
        path = write_menu([
            {"id": "M01", "feature": "Login", "pick": "keep"},
            {"id": "M02", "feature": "Boards", "depends_on": "M01", "pick": "keep"},
        ])
        r = run(path)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("consistent", r.stdout)

    def test_missing_dependency_fails(self):
        path = write_menu([
            {"id": "M01", "feature": "Login", "pick": "drop"},
            {"id": "M02", "feature": "Boards", "depends_on": "M01", "pick": "keep"},
        ])
        r = run(path)
        self.assertEqual(r.returncode, 1)
        self.assertIn("M02 (Boards) needs M01 (Login)", r.stdout)

    def test_conflict_reported_once(self):
        rows = check_menu.load(write_menu([
            {"id": "M01", "feature": "Roles", "conflicts_with": "M02", "pick": "keep"},
            {"id": "M02", "feature": "Open sharing", "conflicts_with": "M01", "pick": "keep"},
        ]))
        _, problems = check_menu.check(rows)
        self.assertEqual(len([p for p in problems if "conflicts" in p]), 1)

    def test_unknown_reference(self):
        rows = check_menu.load(write_menu([
            {"id": "M01", "feature": "Boards", "depends_on": "M99", "pick": "keep"},
        ]))
        _, problems = check_menu.check(rows)
        self.assertTrue(any("unknown id M99" in p for p in problems))

    def test_nothing_kept_fails(self):
        r = run(write_menu([{"id": "M01", "feature": "Login", "pick": "drop"}]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("nothing is marked keep", r.stdout)

    def test_missing_columns_is_bad_file(self):
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
        f.write("feature,pick\nLogin,keep\n")
        f.close()
        self.assertEqual(run(f.name).returncode, 2)

    def test_example_menu_flags_roles(self):
        r = run(EXAMPLE)
        self.assertEqual(r.returncode, 1)
        self.assertIn("M04 (Approval workflow) needs M06", r.stdout)


# --- v2 checks ----------------------------------------------------------------

def errors(rows):
    return vfm.validate(rows, list(rows[0].keys()) + ["merge_type"]).errors


def report(rows):
    return vfm.validate(rows, list(rows[0].keys()) + ["merge_type"])


class MenuStructureTest(unittest.TestCase):
    def test_duplicate_ids(self):
        errs = errors([row("M01", "Login"), row("M01", "Boards")])
        self.assertTrue(any("duplicate id M01" in e for e in errs), errs)

    def test_invalid_pick_is_a_selection_error(self):
        errs = errors([row("M01", "Login", pick="kep")])
        self.assertTrue(any("pick 'kep' is not one of" in e for e in errs), errs)

    def test_circular_dependency(self):
        errs = errors([
            row("M01", "A", depends_on="M02"),
            row("M02", "B", depends_on="M03"),
            row("M03", "C", depends_on="M01"),
        ])
        self.assertTrue(any("circular dependency: M01 -> M02 -> M03 -> M01" in e for e in errs), errs)

    def test_self_dependency_is_circular(self):
        errs = errors([row("M01", "A", depends_on="M01")])
        self.assertTrue(any("circular dependency: M01 -> M01" in e for e in errs), errs)

    def test_transitive_dependency(self):
        errs = errors([
            row("M01", "Dashboard", depends_on="M02"),
            row("M02", "Approvals", depends_on="M03", pick="drop"),
            row("M03", "Roles", pick="later"),
        ])
        self.assertTrue(any("M01 (Dashboard) needs M02 (Approvals)" in e for e in errs), errs)
        self.assertTrue(any("also needs M03 (Roles) through M01 -> M02 -> M03" in e for e in errs), errs)

    def test_transitive_not_repeated_through_kept_step(self):
        errs = errors([
            row("M01", "Dashboard", depends_on="M02"),
            row("M02", "Approvals", depends_on="M03"),
            row("M03", "Roles", pick="drop"),
        ])
        self.assertEqual(len([e for e in errs if "M03" in e]), 1, errs)

    def test_depending_on_skip(self):
        errs = errors([row("M01", "Gallery view", depends_on="M02"),
                       row("M02", "Template marketplace", pick="skip", implementation_strategy="reject")])
        self.assertTrue(any("skipped features cannot be built" in e for e in errs), errs)

    def test_skip_must_be_rejected(self):
        errs = errors([row("M01", "Login"), row("M02", "Marketplace", pick="skip", implementation_strategy="adapt")])
        self.assertTrue(any("is skip (cannot be rebuilt)" in e for e in errs), errs)

    def test_v1_menu_needs_no_v2_columns(self):
        rows = [{"id": "M01", "feature": "Login", "depends_on": "", "conflicts_with": "", "pick": "keep"}]
        self.assertEqual(vfm.validate(rows, list(rows[0])).errors, [])


class MergeGroupTest(unittest.TestCase):
    def test_identical_duplicates_both_kept(self):
        errs = errors([row("M01", "Login (A)", merge_group="sign-in", merge_type="identical"),
                       row("M02", "Login (B)", merge_group="sign-in", merge_type="identical", source_app="B",
                           evidence_refs="B-E01")])
        self.assertTrue(any("identical but keeps M01, M02" in e for e in errs), errs)

    def test_identical_keep_one(self):
        errs = errors([row("M01", "Login (A)", merge_group="sign-in", merge_type="identical"),
                       row("M02", "Login (B)", merge_group="sign-in", merge_type="identical", pick="drop",
                           implementation_strategy="reject")])
        self.assertEqual(errs, [])

    def test_similar_alternatives(self):
        rows = [row("M01", "Flat comments", merge_group="comments", merge_type="similar"),
                row("M02", "Threaded comments", merge_group="comments", merge_type="similar")]
        self.assertTrue(any("choose one alternative" in e for e in errors(rows)))
        for r in rows:
            r["implementation_strategy"] = "combine"
        self.assertEqual(errors(rows), [])

    def test_complementary_features(self):
        rows = [row("M01", "In-app notifications", merge_group="notifications", merge_type="complementary",
                    implementation_strategy="combine"),
                row("M02", "Email notifications", merge_group="notifications", merge_type="complementary",
                    implementation_strategy="combine", source_app="B", evidence_refs="B-E01"),
                row("M03", "Push notifications", merge_group="notifications", merge_type="complementary",
                    implementation_strategy="adapt", source_app="C", evidence_refs="C-E01")]
        rep = report(rows)
        self.assertEqual(rep.errors, [])
        self.assertTrue(any("M03 could be combined" in w for w in rep.warnings), rep.warnings)

    def test_incompatible_features(self):
        errs = errors([
            row("M01", "Role-based access", merge_group="access", merge_type="incompatible", conflicts_with="M02",
                implementation_strategy="rebuild"),
            row("M02", "Anyone-with-link editing", merge_group="access", merge_type="incompatible",
                conflicts_with="M01", implementation_strategy="adapt"),
        ])
        self.assertTrue(any("holds incompatible features but keeps M01, M02" in e for e in errs), errs)
        self.assertTrue(any("M01 (Role-based access) conflicts with M02" in e for e in errs), errs)

    def test_incompatible_needs_conflicts_and_rebuild(self):
        errs = errors([row("M01", "Legacy sync", merge_type="incompatible", implementation_strategy="combine")])
        self.assertTrue(any("conflicts_with does not say what with" in e for e in errs), errs)
        self.assertTrue(any("needs strategy rebuild or adapt" in e for e in errs), errs)

    def test_group_mixes_types(self):
        errs = errors([row("M01", "A", merge_group="x", merge_type="identical"),
                       row("M02", "B", merge_group="x", merge_type="similar", pick="drop")])
        self.assertTrue(any("mixes merge types" in e for e in errs), errs)

    def test_unique_group_with_two_rows(self):
        errs = errors([row("M01", "A", merge_group="x"), row("M02", "B", merge_group="x", pick="drop")])
        self.assertTrue(any("is unique but has 2 features" in e for e in errs), errs)

    def test_similar_needs_a_group(self):
        errs = errors([row("M01", "A", merge_type="similar")])
        self.assertTrue(any("needs a merge_group" in e for e in errs), errs)


class EvidenceAndStrategyTest(unittest.TestCase):
    def test_kept_without_evidence(self):
        errs = errors([row("M01", "Login", evidence_refs="")])
        self.assertTrue(any("has no evidence_refs" in e for e in errs), errs)

    def test_bad_evidence_format(self):
        errs = errors([row("M01", "Login", evidence_refs="screenshot-3")])
        self.assertTrue(any("should look like A-E01" in e for e in errs), errs)

    def test_kept_but_rejected(self):
        errs = errors([row("M01", "Login", implementation_strategy="reject")])
        self.assertTrue(any("is kept but its implementation_strategy is reject" in e for e in errs), errs)

    def test_invalid_values(self):
        errs = errors([row("M01", "Login", implementation_strategy="copy", compatibility="ok", confidence="sure",
                           merge_type="same")])
        for word in ("implementation_strategy 'copy'", "compatibility 'ok'", "confidence 'sure'", "merge_type 'same'"):
            self.assertTrue(any(word in e for e in errs), (word, errs))

    def test_low_confidence_and_conflict_warn(self):
        rep = report([row("M01", "Login", confidence="low", compatibility="conflict")])
        self.assertEqual(rep.errors, [])
        self.assertTrue(any("low-confidence" in w for w in rep.warnings))
        self.assertTrue(any("compatibility conflict" in w for w in rep.warnings))


class SelectionCommandTest(unittest.TestCase):
    def setUp(self):
        self.path = temp_menu([
            row("M01", "Login", pick=""),
            row("M02", "In-app", merge_group="notifications", merge_type="complementary",
                implementation_strategy="combine", pick="", depends_on="M01"),
            row("M03", "Email", merge_group="notifications", merge_type="complementary",
                implementation_strategy="combine", pick="", depends_on="M01"),
            row("M04", "Marketplace", pick="skip", implementation_strategy="reject", priority="could"),
            row("M05", "Approvals", pick="", priority="must"),
        ])

    def tearDown(self):
        os.unlink(self.path)

    def picks(self):
        _, rows = vfm.load_menu(self.path)
        return {r["id"]: r["pick"] for r in rows}

    def test_select_group_and_individuals(self):
        r = run_script("validate_feature_menu.py", self.path, "--set", "keep", "M01,group:notifications")
        self.assertIn("set keep on M01, M02, M03", r.stdout)
        self.assertEqual(self.picks()["M02"], "keep")
        self.assertEqual(self.picks()["M03"], "keep")
        self.assertEqual(self.picks()["M05"], "")

    def test_cannot_keep_skip(self):
        r = run_script("validate_feature_menu.py", self.path, "--set", "keep", "M04")
        self.assertEqual(r.returncode, 2)
        self.assertIn("cannot be kept", r.stdout)
        self.assertEqual(self.picks()["M04"], "skip")

    def test_unknown_target_changes_nothing(self):
        r = run_script("validate_feature_menu.py", self.path, "--set", "keep", "M01,M99")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.picks()["M01"], "")

    def test_dropping_a_must_is_announced(self):
        r = run_script("validate_feature_menu.py", self.path, "--set", "drop", "M05")
        self.assertIn("M05 (Approvals) is a must-have", r.stdout)

    def test_show_groups_in_markdown(self):
        r = run_script("validate_feature_menu.py", self.path, "--show", "--format", "md", "--allow-no-keep")
        self.assertIn("### notifications (complementary)", r.stdout)
        self.assertIn("| ID | Pick | Feature |", r.stdout)
        self.assertEqual(r.returncode, 0, r.stdout)


class SchemaAgreementTest(unittest.TestCase):
    def test_constants_match_feature_schema(self):
        with open(os.path.join(SKILL, "schemas", "feature.schema.json")) as f:
            props = json.load(f)["properties"]
        pairs = {"pick": mixerlib.PICKS, "merge_type": mixerlib.MERGE_TYPES,
                 "implementation_strategy": mixerlib.STRATEGIES, "compatibility": mixerlib.COMPATIBILITY,
                 "confidence": mixerlib.CONFIDENCE, "priority": mixerlib.PRIORITIES,
                 "complexity": mixerlib.COMPLEXITIES}
        pairs["merge_type"] = mixerlib.MERGE_TYPES + tuple(mixerlib.MERGE_SYNONYMS)
        for col, values in pairs.items():
            self.assertEqual([v for v in props[col]["enum"] if v], list(values), col)
        self.assertEqual(sorted(props), sorted(mixerlib.ALL_COLUMNS))

    def test_template_rows_match_schema(self):
        _, rows = vfm.load_menu(EXAMPLE)
        with open(os.path.join(SKILL, "schemas", "feature.schema.json")) as f:
            schema = json.load(f)
        for r in rows:
            clean = {k: v for k, v in r.items() if not k.startswith("__")}
            self.assertEqual(mixerlib.schema_errors(clean, schema), [], r["id"])


if __name__ == "__main__":
    unittest.main()
