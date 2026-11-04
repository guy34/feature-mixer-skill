"""Slice V2: create share links with expiry and open them without signing in."""

from tests.helpers import START, AppTestCase


class CreateLinkTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.alice = self.client("alice")
        self.fid = self.alice.upload("notes.txt", b"one\ntwo\n").json()["id"]

    def test_default_expiry_is_24_hours(self):
        """features: M07
        acceptance: AC09
        expect: a link without expires_in_hours expires exactly 24 h after creation and has a 16-byte url-safe token
        level: feature"""
        r = self.alice.request("POST", f"/api/files/{self.fid}/links", json_body={})
        self.assertEqual(r.status, 201)
        body = r.json()
        self.assertEqual(body["expires_at"], START + 24 * 3600)
        self.assertEqual(body["url"], "/s/" + body["token"])
        self.assertFalse(body["has_password"])
        self.assertEqual(len(body["token"]), 22)  # token_urlsafe(16)

    def test_custom_expiry_and_validation(self):
        """features: M07
        acceptance: AC09
        expect: positive hours are honoured; 0, negative, text, booleans and null are 400 invalid_expiry
        level: form"""
        r = self.alice.request("POST", f"/api/files/{self.fid}/links", json_body={"expires_in_hours": 2})
        self.assertEqual(r.json()["expires_at"], START + 7200)
        r = self.alice.request("POST", f"/api/files/{self.fid}/links", json_body={"expires_in_hours": 0.5})
        self.assertEqual(r.json()["expires_at"], START + 1800)
        for bad in (0, -1, "24", True, None):
            r = self.alice.request("POST", f"/api/files/{self.fid}/links", json_body={"expires_in_hours": bad})
            self.assertEqual(r.status, 400, bad)
            self.assertEqual(r.json()["error"]["code"], "invalid_expiry")

    def test_only_the_owner_can_create_links(self):
        """features: M07
        acceptance: AC09
        expect: another user creating a link to alice's file gets 404 and no link is stored; unknown files are 404
        level: auth"""
        bob = self.client("bob")
        self.assertEqual(bob.request("POST", f"/api/files/{self.fid}/links", json_body={}).status, 404)
        self.assertEqual(self.alice.request("POST", "/api/files/doesnotexist/links", json_body={}).status, 404)
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        self.assertEqual(conn.execute("SELECT count(*) FROM share_links").fetchone()[0], 0)
        conn.close()

    def test_expired_link_is_404(self):
        """features: M07, M09
        acceptance: AC09
        expect: a link opens up to its expiry second and answers 404 not_found after it
        level: feature"""
        token = self.alice.request("POST", f"/api/files/{self.fid}/links",
                                   json_body={"expires_in_hours": 1}).json()["token"]
        anon = self.client()
        self.clock.advance(3600)
        self.assertEqual(anon.request("GET", f"/api/share/{token}").status, 200)
        self.clock.advance(1)
        r = anon.request("GET", f"/api/share/{token}")
        self.assertEqual(r.status, 404)
        self.assertEqual(r.json()["error"]["code"], "not_found")
        self.assertEqual(anon.request("GET", f"/api/share/{token}/content").status, 404)


class OpenLinkTests(AppTestCase):
    def test_anonymous_open_shows_metadata_and_preview(self):
        """features: M09, M04
        acceptance: AC11
        expect: without a session the link returns name, size, content type and the text preview
        level: interaction"""
        alice = self.client("alice")
        fid = alice.upload("notes.md", b"# Title\nbody\n").json()["id"]
        token = alice.request("POST", f"/api/files/{fid}/links", json_body={}).json()["token"]
        anon = self.client()
        r = anon.request("GET", f"/api/share/{token}")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.json(), {"name": "notes.md", "size": 13, "content_type": "text/markdown",
                                    "preview": {"kind": "text", "first_lines": ["# Title", "body"]}})

    def test_anonymous_download(self):
        """features: M09
        acceptance: AC11
        expect: the content route returns the exact bytes as an attachment for non-image types
        level: api"""
        alice = self.client("alice")
        data = bytes(range(256))
        fid = alice.upload("blob.bin", data).json()["id"]
        token = alice.request("POST", f"/api/files/{fid}/links", json_body={}).json()["token"]
        r = self.client().request("GET", f"/api/share/{token}/content")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, data)
        self.assertTrue(r.header("Content-Disposition").startswith("attachment"))
        self.assertEqual(r.header("X-Content-Type-Options"), "nosniff")

    def test_unknown_token_is_404(self):
        """features: M09
        acceptance: AC11
        expect: an unknown token answers 404 with the same message as an expired one
        level: api"""
        r = self.client().request("GET", "/api/share/notarealtoken")
        self.assertEqual(r.status, 404)
        self.assertEqual(r.json()["error"]["message"], "link expired or unknown")

    def test_link_gives_access_to_one_file_only(self):
        """features: M09, M02
        expect: a link holder cannot list the owner's files or reach other files through owner routes
        level: auth"""
        alice = self.client("alice")
        f1 = alice.upload("one.txt", b"1").json()["id"]
        f2 = alice.upload("two.txt", b"2").json()["id"]
        token = alice.request("POST", f"/api/files/{f1}/links", json_body={}).json()["token"]
        anon = self.client()
        self.assertEqual(anon.request("GET", f"/api/share/{token}").json()["name"], "one.txt")
        self.assertEqual(anon.request("GET", "/api/files").status, 401)
        self.assertEqual(anon.request("GET", f"/api/files/{f2}/content").status, 401)
