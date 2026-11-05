import unittest
import files as m


class Clock:
    def __init__(self):
        self.t = 1_000.0

    def __call__(self):
        return self.t


class FilesHoldout(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.app = m.create_app(self.clock)
        self.fid = self.app.upload("ana", "plan.txt", b"secret plan " * 20)

    def test_owner_previews(self):
        self.assertEqual(self.app.preview("ana", self.fid), (b"secret plan " * 20)[:64])

    def test_private_by_default(self):
        with self.assertRaises(PermissionError):
            self.app.preview("bo", self.fid)
        with self.assertRaises(PermissionError):
            self.app.share("bo", self.fid, 60)

    def test_links_expire(self):
        t = self.app.share("ana", self.fid, 60)
        self.assertTrue(self.app.open_link(t).startswith(b"secret"))
        self.clock.t += 61
        with self.assertRaises(PermissionError):
            self.app.open_link(t)

    def test_unknown_links_fail(self):
        with self.assertRaises(PermissionError):
            self.app.open_link("guessed-token")

    def test_delete_revokes_links_and_previews(self):
        t = self.app.share("ana", self.fid, 3600)
        self.app.attach("ana", "n1", self.fid)
        with self.assertRaises(PermissionError):
            self.app.delete("bo", self.fid)
        self.app.delete("ana", self.fid)
        with self.assertRaises(PermissionError):
            self.app.open_link(t)
        with self.assertRaises(KeyError):
            self.app.preview("ana", self.fid)
        self.assertEqual(self.app.attachments("ana", "n1"), [{"file": self.fid, "status": "deleted"}])

    def test_ids_are_opaque(self):
        other = self.app.upload("ana", "b.txt", b"b")
        self.assertNotEqual(str(other), str(self.fid))
        self.assertFalse(str(self.fid).isdigit(), "sequential numeric ids let people guess other files")
