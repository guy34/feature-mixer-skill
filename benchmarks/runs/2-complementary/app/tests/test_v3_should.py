"""Slice V3: delete (with link cascade), image preview, link passwords, revoke."""

import hashlib
import sqlite3

from tests.helpers import AppTestCase

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32


class DeleteTests(AppTestCase):
    def test_delete_removes_file_and_its_links(self):
        """features: M03, M09
        acceptance: AC05
        expect: 204; the file leaves the list, its bytes are gone, and its share link answers 404
        level: database"""
        alice = self.client("alice")
        fid = alice.upload("a.txt", b"x").json()["id"]
        token = alice.request("POST", f"/api/files/{fid}/links", json_body={}).json()["token"]
        self.assertEqual(alice.request("DELETE", f"/api/files/{fid}").status, 204)
        self.assertEqual(alice.request("GET", "/api/files").json()["files"], [])
        self.assertEqual(self.client().request("GET", f"/api/share/{token}").status, 404)
        conn = sqlite3.connect(self.db_path)
        counts = [conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("file_content", "share_links")]
        conn.close()
        self.assertEqual(counts, [0, 0])
        self.assertEqual(alice.request("DELETE", f"/api/files/{fid}").status, 404)

    def test_cannot_delete_someone_elses_file(self):
        """features: M03
        acceptance: AC05
        expect: bob deleting alice's file gets 404 and alice still has it
        level: auth"""
        alice, bob = self.client("alice"), self.client("bob")
        fid = alice.upload("a.txt", b"x").json()["id"]
        self.assertEqual(bob.request("DELETE", f"/api/files/{fid}").status, 404)
        self.assertEqual(len(alice.request("GET", "/api/files").json()["files"]), 1)


class ImagePreviewTests(AppTestCase):
    def test_image_preview_url_serves_the_image(self):
        """features: M05
        acceptance: AC07
        expect: .png/.jpg/.gif preview as kind image; the URL serves the bytes inline with an image content type
        level: feature"""
        alice = self.client("alice")
        for name, ctype in (("pic.png", "image/png"), ("PHOTO.JPG", "image/jpeg"), ("anim.gif", "image/gif")):
            fid = alice.upload(name, PNG).json()["id"]
            p = alice.request("GET", f"/api/files/{fid}/preview").json()
            self.assertEqual(p, {"kind": "image", "url": f"/api/files/{fid}/content"})
            r = alice.request("GET", p["url"])
            self.assertEqual(r.status, 200)
            self.assertEqual(r.header("Content-Type"), ctype)
            self.assertTrue(r.header("Content-Disposition").startswith("inline"))
            self.assertEqual(r.body, PNG)

    def test_image_preview_through_a_share_link(self):
        """features: M05, M09
        acceptance: AC07
        expect: a shared image previews with a link-scoped URL that serves the image without a session
        level: interaction"""
        alice = self.client("alice")
        fid = alice.upload("pic.gif", PNG).json()["id"]
        token = alice.request("POST", f"/api/files/{fid}/links", json_body={}).json()["token"]
        anon = self.client()
        p = anon.request("GET", f"/api/share/{token}").json()["preview"]
        self.assertEqual(p, {"kind": "image", "url": f"/api/share/{token}/content"})
        r = anon.request("GET", p["url"])
        self.assertEqual((r.status, r.header("Content-Type"), r.body), (200, "image/gif", PNG))

    def test_svg_and_html_are_downloads_not_inline(self):
        """features: M05, M06
        expect: types outside png/jpg/gif (svg, html) get no image preview and are served as attachments
        level: feature"""
        alice = self.client("alice")
        for name in ("x.svg", "x.html"):
            fid = alice.upload(name, b"<svg onload=alert(1)>").json()["id"]
            self.assertEqual(alice.request("GET", f"/api/files/{fid}/preview").json()["kind"], "none")
            r = alice.request("GET", f"/api/files/{fid}/content")
            self.assertTrue(r.header("Content-Disposition").startswith("attachment"), name)


class PasswordLinkTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.alice = self.client("alice")
        self.fid = self.alice.upload("secret.txt", b"top secret").json()["id"]
        r = self.alice.request("POST", f"/api/files/{self.fid}/links", json_body={"password": "open sesame"})
        self.assertEqual(r.status, 201)
        self.assertTrue(r.json()["has_password"])
        self.token = r.json()["token"]

    def test_password_required_and_checked(self):
        """features: M08, M09
        acceptance: AC10
        expect: no password is 403 password_required, a wrong one 403 wrong_password, the right one opens metadata and content
        level: feature"""
        anon = self.client()
        r = anon.request("GET", f"/api/share/{self.token}")
        self.assertEqual((r.status, r.json()["error"]["code"]), (403, "password_required"))
        r = anon.request("GET", f"/api/share/{self.token}", headers={"X-Link-Password": "nope"})
        self.assertEqual((r.status, r.json()["error"]["code"]), (403, "wrong_password"))
        r = anon.request("GET", f"/api/share/{self.token}/content", headers={"X-Link-Password": "nope"})
        self.assertEqual(r.status, 403)
        ok = {"X-Link-Password": "open sesame"}
        self.assertEqual(anon.request("GET", f"/api/share/{self.token}", headers=ok).json()["name"], "secret.txt")
        self.assertEqual(anon.request("GET", f"/api/share/{self.token}/content", headers=ok).body, b"top secret")

    def test_password_stored_as_salted_slow_hash(self):
        """features: M08
        acceptance: AC10
        expect: the stored hash is pbkdf2_sha256 with a salt, not ShareLink's unsalted SHA-256 hex, and two links with the same password differ
        level: database"""
        r = self.alice.request("POST", f"/api/files/{self.fid}/links", json_body={"password": "open sesame"})
        conn = sqlite3.connect(self.db_path)
        hashes = [row[0] for row in conn.execute("SELECT password_hash FROM share_links")]
        conn.close()
        self.assertEqual(r.status, 201)
        self.assertEqual(len(hashes), 2)
        self.assertNotEqual(hashes[0], hashes[1])
        for h in hashes:
            self.assertTrue(h.startswith("pbkdf2_sha256$"))
            self.assertNotEqual(h, hashlib.sha256(b"open sesame").hexdigest())

    def test_invalid_password_value(self):
        """features: M08
        expect: an empty or non-string password is 400 invalid_password
        level: form"""
        for bad in ("", 123):
            r = self.alice.request("POST", f"/api/files/{self.fid}/links", json_body={"password": bad})
            self.assertEqual((r.status, r.json()["error"]["code"]), (400, "invalid_password"))


class RevokeTests(AppTestCase):
    def test_owner_revokes_link(self):
        """features: M10, M09
        acceptance: AC12
        expect: 204, after which the link answers 404; revoking again is 404
        level: feature"""
        alice = self.client("alice")
        fid = alice.upload("a.txt", b"x").json()["id"]
        token = alice.request("POST", f"/api/files/{fid}/links", json_body={}).json()["token"]
        self.assertEqual(alice.request("DELETE", f"/api/links/{token}").status, 204)
        self.assertEqual(self.client().request("GET", f"/api/share/{token}").status, 404)
        self.assertEqual(alice.request("DELETE", f"/api/links/{token}").status, 404)

    def test_other_user_cannot_revoke(self):
        """features: M10
        acceptance: AC12
        expect: bob revoking alice's link gets 404 and the link keeps working
        level: auth"""
        alice, bob = self.client("alice"), self.client("bob")
        fid = alice.upload("a.txt", b"x").json()["id"]
        token = alice.request("POST", f"/api/files/{fid}/links", json_body={}).json()["token"]
        self.assertEqual(bob.request("DELETE", f"/api/links/{token}").status, 404)
        self.assertEqual(self.client().request("GET", f"/api/share/{token}").status, 200)
