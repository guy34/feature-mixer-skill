"""The WSGI application: routing table, per-request database connection, HTML pages."""

import logging
import os
import re
import time

from . import accounts, files, preview, sharing
from .config import Config
from .core import db
from .core.http import HTTPError, Request, Response, error_response

log = logging.getLogger("fileshare")
STATIC = os.path.join(os.path.dirname(__file__), "static")
SEG = r"([A-Za-z0-9_-]{1,128})"


def _page(name):
    def handler(ctx, req, *args):
        with open(os.path.join(STATIC, name), "rb") as f:
            return Response(200, f.read(), "text/html; charset=utf-8",
                            [("Content-Security-Policy", "default-src 'self'; img-src 'self' blob:; "
                              "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"),
                             ("Referrer-Policy", "no-referrer")])
    return handler


ROUTES = [
    ("GET", r"/", _page("index.html")),
    ("GET", r"/s/" + SEG, _page("share.html")),
    ("POST", r"/api/register", accounts.register),
    ("POST", r"/api/login", accounts.login),
    ("POST", r"/api/logout", accounts.logout),
    ("GET", r"/api/files", files.list_files),
    ("POST", r"/api/files", files.upload),
    ("DELETE", r"/api/files/" + SEG, files.delete_file),
    ("GET", r"/api/files/" + SEG + r"/content", files.file_content),
    ("GET", r"/api/files/" + SEG + r"/preview", preview.owner_preview),
    ("POST", r"/api/files/" + SEG + r"/links", sharing.create_link),
    ("DELETE", r"/api/links/" + SEG, sharing.revoke_link),
    ("GET", r"/api/share/" + SEG, sharing.shared_file),
    ("GET", r"/api/share/" + SEG + r"/content", sharing.shared_content),
]
COMPILED = [(m, re.compile("^" + p + "$"), h, p) for m, p, h in ROUTES]


class Context:
    def __init__(self, app, conn):
        self.config, self.clock, self.db = app.config, app.clock, conn


class App:
    def __init__(self, config=None, clock=time.time):
        self.config = config or Config.from_env()
        self.clock = clock
        db.init_db(self.config.db_path)

    def __call__(self, environ, start_response):
        req = Request(environ)
        template = "?"
        conn = db.connect(self.config.db_path)
        try:
            matched = [(m, rx.match(req.path), h, p) for m, rx, h, p in COMPILED]
            matched = [(m, mm, h, p) for m, mm, h, p in matched if mm]
            hit = next(((mm, h, p) for m, mm, h, p in matched if m == req.method), None)
            if hit:
                mm, handler, template = hit
                resp = handler(Context(self, conn), req, *mm.groups())
            elif matched:
                raise HTTPError(405, "method_not_allowed", "method not allowed")
            else:
                raise HTTPError(404, "not_found", "no such route")
        except HTTPError as e:
            conn.rollback()
            resp = error_response(e)
        except Exception:  # never leak internals; log route only, no personal data
            conn.rollback()
            log.exception("unhandled error on %s %s", req.method, template)
            resp = error_response(HTTPError(500, "server_error", "something went wrong"))
        finally:
            conn.close()
        log.info("%s %s -> %s", req.method, template, resp.status)
        return resp.wsgi(start_response)
