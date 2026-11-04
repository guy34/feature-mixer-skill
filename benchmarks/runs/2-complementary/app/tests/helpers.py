"""In-process WSGI client and a fake clock for the FileShare tests (no sockets, temp SQLite files)."""

import io
import json
import os
import shutil
import tempfile
import unittest
from http.cookies import SimpleCookie
from urllib.parse import urlsplit

from fileshare import App
from fileshare.config import Config

START = 1_800_000_000.0


class FakeClock:
    def __init__(self, now=START):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class Result:
    def __init__(self, status, headers, body):
        self.status, self.headers, self.body = status, headers, body

    def header(self, name):
        for k, v in self.headers:
            if k.lower() == name.lower():
                return v
        return None

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class Client:
    """One browser: keeps its own cookies."""

    def __init__(self, app):
        self.app, self.cookies = app, {}

    def request(self, method, url, body=None, json_body=None, headers=None, content_length=True):
        parts = urlsplit(url)
        if json_body is not None:
            body = json.dumps(json_body).encode()
        body = body or b""
        environ = {
            "REQUEST_METHOD": method, "PATH_INFO": parts.path, "QUERY_STRING": parts.query,
            "wsgi.input": io.BytesIO(body), "SERVER_NAME": "test", "SERVER_PORT": "80", "wsgi.url_scheme": "http",
        }
        if content_length and (body or method in ("POST", "PUT", "PATCH")):
            environ["CONTENT_LENGTH"] = str(len(body))
        if json_body is not None:
            environ["CONTENT_TYPE"] = "application/json"
        if self.cookies:
            environ["HTTP_COOKIE"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        for k, v in (headers or {}).items():
            environ["HTTP_" + k.upper().replace("-", "_")] = v
        captured = {}

        def start_response(status, hdrs):
            captured["status"], captured["headers"] = int(status.split()[0]), hdrs

        out = b"".join(self.app(environ, start_response))
        res = Result(captured["status"], captured["headers"], out)
        for k, v in res.headers:
            if k.lower() == "set-cookie":
                c = SimpleCookie()
                c.load(v)
                for name, m in c.items():
                    if m["max-age"] == "0" or not m.value:
                        self.cookies.pop(name, None)
                    else:
                        self.cookies[name] = m.value
        return res

    # shortcuts
    def register(self, username, password="correct horse"):
        return self.request("POST", "/api/register", json_body={"username": username, "password": password})

    def upload(self, name, data):
        from urllib.parse import quote
        return self.request("POST", "/api/files?name=" + quote(name), body=data)


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fileshare-test-")
        self.db_path = os.path.join(self.tmp, "test.sqlite3")
        self.clock = FakeClock()
        # fewer PBKDF2 iterations keep the suite fast; the stored format records the count
        self.app = App(Config(db_path=self.db_path, pbkdf2_iterations=1000), clock=self.clock)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def client(self, username=None):
        c = Client(self.app)
        if username:
            r = c.register(username)
            self.assertEqual(r.status, 201, r.body)
        return c
