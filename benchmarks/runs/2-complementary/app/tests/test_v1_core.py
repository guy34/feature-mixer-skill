"""Slice V1: sign in, upload, list, text preview and the no-preview fallback."""

import sqlite3

from tests.helpers import AppTestCase

TEN_MB = 10 * 1024 * 1024


class AccountsTests(AppTestCase):
    def test_register_login_logout(self):
        """features: M01, M02
        expect: register sets an http-only session cookie; logout ends it; login with the right password restores it
        level: auth"""
        c = self.client()
        r = c.register("alice")
        self.assertEqual(r.status, 201)
        cookie = r.header("Set-Cookie")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertEqual(c.request("GET", "/api/files").status, 200)
        self.assertEqual(c.request("POST", "/api/logout").status, 204)
        self.assertEqual(c.request("GET", "/api/files").status, 401)
        r = c.request("POST", "/api/login", json_body={"username": "alice", "password": "correct horse"})
        self.assertEqual(r.status, 200)
        self.assertEqual(c.request("GET", "/api/files").status, 200)

    def test_wrong_password_and_duplicate_username(self):
        """features: M01
        expect: wrong password is 401 bad_credentials; a taken username is 409; short passwords are 400
        level: auth"""
        self.client("alice")
        c = self.client()
        r = c.request("POST", "/api/login", json_body={"username": "alice", "password": "wrong password"})
        self.assertEqual(r.status, 401)
        self.assertEqual(r.json()["error"]["code"], "bad_credentials")
        self.assertEqual(c.register("alice").status, 409)
        self.assertEqual(c.register("bob", "short").status, 400)
        self.assertEqual(c.register("x").status, 400)

    def test_session_expires(self):
        """features: M02
        expect: a session older than 7 days answers 401
        level: auth"""
        c = self.client("alice")
        self.clock.advance(7 * 24 * 3600 + 1)
        self.assertEqual(c.request("GET", "/api/files").status, 401)

    def test_account_password_is_salted_pbkdf2(self):
        """features: M01
        expect: account passwords are stored as pbkdf2_sha256 with a per-user salt, never in plain text
        level: database"""
        self.client("alice")
        self.client("bob")
        conn = sqlite3.connect(self.db_path)
        hashes = [r[0] for r in conn.execute("SELECT password_hash FROM users")]
        conn.close()
        self.assertTrue(all(h.startswith("pbkdf2_sha256$") for h in hashes))
        self.assertNotEqual(hashes[0].split("$")[2], hashes[1].split("$")[2])
        self.assertFalse(any("correct horse" in h for h in hashes))


class UploadTests(AppTestCase):
    def test_upload_returns_file(self):
        """features: M01
        acceptance: AC01
        expect: 201 with id, name, size and a guessed content type
        level: api"""
        c = self.client("alice")
        r = c.upload("notes.txt", b"hello\nworld\n")
        self.assertEqual(r.status, 201)
        body = r.json()
        self.assertEqual(body["name"], "notes.txt")
        self.assertEqual(body["size"], 12)
        self.assertEqual(body["content_type"], "text/plain")
        self.assertEqual(len(body["id"]), 32)

    def test_upload_limit_is_10_mb(self):
        """features: M01
        acceptance: AC02
        expect: exactly 10485760 bytes is accepted; 10485761 is 413 file_too_large and nothing is stored
        level: feature"""
        c = self.client("alice")
        self.assertEqual(c.upload("exact.bin", b"\0" * TEN_MB).status, 201)
        r = c.upload("big.bin", b"\0" * (TEN_MB + 1))
        self.assertEqual(r.status, 413)
        self.assertEqual(r.json()["error"]["code"], "file_too_large")
        names = [f["name"] for f in c.request("GET", "/api/files").json()["files"]]
        self.assertEqual(names, ["exact.bin"])

    def test_upload_rejects_oversize_content_length_before_reading(self):
        """features: M01
        acceptance: AC02
        expect: a Content-Length over the limit is refused with 413 without reading the body
        level: api"""
        c = self.client("alice")
        environ_len = str(TEN_MB + 1)

        class Exploding:
            def read(self, n=-1):
                raise AssertionError("body must not be read")

        import io  # noqa: F401
        captured = {}
        env = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/files", "QUERY_STRING": "name=a.bin",
               "CONTENT_LENGTH": environ_len, "wsgi.input": Exploding(),
               "HTTP_COOKIE": "; ".join(f"{k}={v}" for k, v in c.cookies.items())}
        self.app(env, lambda s, h: captured.setdefault("status", int(s.split()[0])))
        self.assertEqual(captured["status"], 413)

    def test_upload_validation(self):
        """features: M01
        expect: missing or unsafe names are 400 invalid_name; a missing Content-Length is 411
        level: form"""
        c = self.client("alice")
        self.assertEqual(c.request("POST", "/api/files", body=b"x").json()["error"]["code"], "invalid_name")
        self.assertEqual(c.upload("../evil.txt", b"x").status, 400)
        self.assertEqual(c.upload("a" * 256, b"x").status, 400)
        r = c.request("POST", "/api/files?name=a.txt", body=b"", content_length=False)
        self.assertEqual(r.status, 411)
        self.assertEqual(c.upload("empty.txt", b"").status, 201)

    def test_file_endpoints_need_sign_in(self):
        """features: M01, M02, M03, M04, M07
        acceptance: AC03
        expect: every owner endpoint answers 401 with the JSON error shape when nobody is signed in
        level: auth"""
        anon = self.client()
        for method, path in [("GET", "/api/files"), ("POST", "/api/files?name=a.txt"),
                             ("DELETE", "/api/files/abc"), ("GET", "/api/files/abc/preview"),
                             ("GET", "/api/files/abc/content"), ("POST", "/api/files/abc/links"),
                             ("DELETE", "/api/links/abc"), ("POST", "/api/logout")]:
            r = anon.request(method, path, body=b"x" if method == "POST" else None)
            self.assertEqual(r.status, 401, (method, path))
            self.assertEqual(r.json()["error"]["code"], "not_signed_in")


class ListTests(AppTestCase):
    def test_each_user_sees_only_their_files(self):
        """features: M02
        acceptance: AC04
        expect: two users each list only their own files, newest first
        level: auth"""
        alice, bob = self.client("alice"), self.client("bob")
        alice.upload("a1.txt", b"1")
        self.clock.advance(1)
        alice.upload("a2.txt", b"2")
        bob.upload("b1.txt", b"3")
        self.assertEqual([f["name"] for f in alice.request("GET", "/api/files").json()["files"]], ["a2.txt", "a1.txt"])
        self.assertEqual([f["name"] for f in bob.request("GET", "/api/files").json()["files"]], ["b1.txt"])

    def test_empty_list(self):
        """features: M02
        expect: a new user gets an empty list
        level: feature"""
        self.assertEqual(self.client("alice").request("GET", "/api/files").json(), {"files": []})


class TextPreviewTests(AppTestCase):
    def test_text_preview_first_20_lines(self):
        """features: M04
        acceptance: AC06
        expect: .txt, .md and .csv (any case) preview as kind text with at most 20 lines
        level: feature"""
        c = self.client("alice")
        lines = "\n".join(f"line {i}" for i in range(25)).encode()
        for name in ("a.txt", "B.MD", "c.Csv"):
            fid = c.upload(name, lines).json()["id"]
            p = c.request("GET", f"/api/files/{fid}/preview").json()
            self.assertEqual(p["kind"], "text", name)
            self.assertEqual(len(p["first_lines"]), 20)
            self.assertEqual(p["first_lines"][0], "line 0")
            self.assertEqual(p["first_lines"][-1], "line 19")

    def test_text_preview_replaces_invalid_utf8(self):
        """features: M04
        acceptance: AC06
        expect: undecodable bytes become replacement characters instead of an error
        level: feature"""
        c = self.client("alice")
        fid = c.upload("bad.txt", b"ok \xff\xfe end").json()["id"]
        p = c.request("GET", f"/api/files/{fid}/preview").json()
        self.assertEqual(p["first_lines"], ["ok �� end"])

    def test_preview_of_someone_elses_file_is_404(self):
        """features: M04
        expect: previewing another user's file answers 404 not_found
        level: auth"""
        alice, bob = self.client("alice"), self.client("bob")
        fid = alice.upload("a.txt", b"secret").json()["id"]
        r = bob.request("GET", f"/api/files/{fid}/preview")
        self.assertEqual(r.status, 404)
        self.assertEqual(r.json()["error"]["code"], "not_found")


class FallbackPreviewTests(AppTestCase):
    def test_other_types_have_no_preview(self):
        """features: M06
        acceptance: AC08
        expect: .pdf, .zip and extensionless files preview as kind none with the reason
        level: feature"""
        c = self.client("alice")
        for name in ("doc.pdf", "a.zip", "README"):
            fid = c.upload(name, b"data").json()["id"]
            p = c.request("GET", f"/api/files/{fid}/preview").json()
            self.assertEqual(p, {"kind": "none", "reason": "no preview for this type"}, name)


class PlatformTests(AppTestCase):
    def test_schema_created_from_empty_with_foreign_keys(self):
        """features: M01
        expect: every table exists after start and foreign keys cascade from files
        level: database"""
        conn = sqlite3.connect(self.db_path)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        fks = conn.execute("PRAGMA foreign_key_list(share_links)").fetchall()
        conn.close()
        self.assertTrue({"users", "sessions", "files", "file_content", "share_links"} <= tables)
        self.assertTrue(any(fk[2] == "files" and fk[6] == "CASCADE" for fk in fks))

    def test_pages_and_unknown_routes(self):
        """features: M02, M09
        expect: / and /s/<token> serve HTML; unknown routes are 404 and wrong methods 405, both in the JSON error shape
        level: navigation"""
        c = self.client()
        r = c.request("GET", "/")
        self.assertEqual(r.status, 200)
        self.assertIn(b"<title>FileShare</title>", r.body)
        self.assertIn("text/html", r.header("Content-Type"))
        self.assertEqual(c.request("GET", "/s/sometoken").status, 200)
        self.assertEqual(c.request("GET", "/nope").json()["error"]["code"], "not_found")
        self.assertEqual(c.request("PUT", "/api/files").status, 405)

    def test_invalid_json_is_400(self):
        """features: M07
        expect: a malformed JSON body answers 400 invalid_json
        level: api"""
        c = self.client()
        r = c.request("POST", "/api/register", body=b"{nope")
        self.assertEqual(r.status, 400)
        self.assertEqual(r.json()["error"]["code"], "invalid_json")
