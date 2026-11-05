import unittest
import contacts as m
import transport as t


class ApiHoldout(unittest.TestCase):
    def setUp(self):
        self.tr = t.MockTransport()
        self.slept = []
        self.c = m.create_client(self.tr, "tok", "key", self.slept.append)

    def test_every_page_of_both_apis(self):
        got = self.c.list_all()
        self.assertEqual(sorted((x["source"], x["id"]) for x in got),
                         sorted([("A", str(i)) for i in range(1, 6)] + [("B", f"b{i}") for i in range(1, 6)]))
        self.assertTrue(all(x["name"] for x in got))

    def test_rate_limit_is_respected(self):
        self.c.list_all()
        self.assertEqual(self.slept, [7])

    def test_get_and_not_found(self):
        self.assertEqual(self.c.get("B", "b2")["name"], "B person 2")
        for src, i in (("A", "99"), ("B", "nope")):
            with self.assertRaises(m.NotFound):
                self.c.get(src, i)

    def test_unavailable_delete_is_reported(self):
        with self.assertRaises(m.NotSupported):
            self.c.delete("B", "b1")
        self.c.delete("A", "1")
        with self.assertRaises(m.NotFound):
            self.c.get("A", "1")

    def test_errors_are_mapped(self):
        bad = m.create_client(t.MockTransport(rate_limit_once=False), "wrong", "wrong", self.slept.append)
        for src in ("A", "B"):
            with self.assertRaises(m.ApiError) as e:
                bad.get(src, "1")
            self.assertEqual((e.exception.source, e.exception.status), (src, 401))

    def test_only_documented_endpoints_are_called(self):
        self.c.list_all()
        self.c.get("A", "2")
        try:
            self.c.delete("B", "b1")
        except m.NotSupported:
            pass
        self.assertTrue(set(self.tr.calls) <= t.MockTransport.ALLOWED, set(self.tr.calls) - t.MockTransport.ALLOWED)
