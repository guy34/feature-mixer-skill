import unittest
import documents as m


class RulesHoldout(unittest.TestCase):
    def setUp(self):
        self.app = m.create_app()
        for u, r in (("ana", "author"), ("bo", "author"), ("root", "admin")):
            self.app.add_user(u, r)
        self.doc = self.app.create("ana", "v1")

    def test_author_edits_own_draft(self):
        self.app.edit("ana", self.doc, "v2")
        self.assertEqual(self.app.get(self.doc)["text"], "v2")

    def test_others_never_edit_a_draft(self):
        with self.assertRaises(PermissionError):
            self.app.edit("bo", self.doc, "mine now")

    def test_author_cannot_edit_after_submit(self):
        self.app.submit("ana", self.doc)
        with self.assertRaises(m.Locked):
            self.app.edit("ana", self.doc, "late change")
        self.assertEqual(self.app.get(self.doc)["text"], "v1")

    def test_admin_override_needs_a_reason(self):
        self.app.submit("ana", self.doc)
        with self.assertRaises(m.Locked):
            self.app.edit("root", self.doc, "fix")
        for empty in ("", "   "):
            with self.assertRaises(m.Locked):
                self.app.edit("root", self.doc, "fix", reason=empty)

    def test_admin_override_with_a_reason_is_recorded(self):
        self.app.submit("ana", self.doc)
        self.app.edit("root", self.doc, "fixed typo", reason="typo in the title")
        self.assertEqual(self.app.get(self.doc)["text"], "fixed typo")
        self.assertIn({"user": "root", "action": "override", "reason": "typo in the title"},
                      [{k: e.get(k) for k in ("user", "action", "reason")} for e in self.app.audit(self.doc)])

    def test_other_authors_cannot_override(self):
        self.app.submit("ana", self.doc)
        with self.assertRaises((PermissionError, m.Locked)):
            self.app.edit("bo", self.doc, "x", reason="because")
