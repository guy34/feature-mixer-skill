"""The JSON API (architecture.json "api"), on the standard library's HTTP server.

Errors always look like {"error": {"code": "...", "message": "..."}}.
Sign-in sets an http-only session cookie (D02). Behind HTTPS, add the
Secure flag (set TEAMHUB_SECURE_COOKIE=1).
"""

import json
import os
import re
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import approvals, auth, comments, dashboard, notifications, tasks
from .errors import AppError, Invalid, MethodNotAllowed, NotFound

ID = r"(?P<id>[0-9a-f-]{36})"


class App:
    """Turns (method, path, body, cookie) into (status, headers, payload)."""

    def __init__(self, conn):
        self.conn = conn
        self.lock = threading.Lock()
        self.routes = [
            ("POST", r"/api/session", self.sign_in, False),
            ("DELETE", r"/api/session", self.sign_out, True),
            ("GET", r"/api/me", self.me, True),
            ("POST", r"/api/users", self.create_user, True),
            ("PATCH", r"/api/me/notification-settings", self.notification_settings, True),
            ("GET", r"/api/tasks", self.list_tasks, True),
            ("POST", r"/api/tasks", self.create_task, True),
            ("PATCH", rf"/api/tasks/{ID}", self.update_task, True),
            ("POST", rf"/api/tasks/{ID}/approvals", self.request_approval, True),
            ("GET", r"/api/approvals", self.list_approvals, True),
            ("POST", rf"/api/approvals/{ID}/decision", self.decide, True),
            ("GET", rf"/api/(?P<kind>tasks|approvals)/{ID}/comments", self.thread, True),
            ("POST", rf"/api/(?P<kind>tasks|approvals)/{ID}/comments", self.comment, True),
            ("GET", r"/api/notifications", self.list_notifications, True),
            ("POST", rf"/api/notifications/{ID}/read", self.read_notification, True),
            ("POST", r"/api/push-subscriptions", self.subscribe_push, True),
            ("GET", r"/api/dashboard", self.dashboard, True),
        ]

    def handle(self, method, raw_path, body=b"", cookie_header=""):
        url = urlparse(raw_path)
        path = url.path.rstrip("/") or "/"
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header or "")
        except Exception:
            pass
        token = cookie["session"].value if "session" in cookie else None
        try:
            route = self._match(method, path)
            if route is None:
                raise NotFound("no such endpoint")
            handler, needs_user, params = route
            data = self._json(body)
            with self.lock:
                user = auth.user_for_session(self.conn, token) if needs_user else None
                return handler(user=user, params=params, data=data, query=query, token=token)
        except AppError as e:
            return e.status, [], {"error": {"code": e.code, "message": e.message}}
        except Exception:
            return 500, [], {"error": {"code": "server_error", "message": "something went wrong"}}

    def _match(self, method, path):
        allowed = False
        for m, pattern, handler, needs_user in self.routes:
            hit = re.fullmatch(pattern, path)
            if hit:
                allowed = True
                if m == method:
                    return handler, needs_user, hit.groupdict()
        if allowed:
            raise MethodNotAllowed("this endpoint does not accept that method")
        return None

    @staticmethod
    def _json(body):
        if not body:
            return {}
        try:
            data = json.loads(body)
        except ValueError:
            raise Invalid("the request body must be JSON")
        if not isinstance(data, dict):
            raise Invalid("the request body must be a JSON object")
        return data

    # accounts
    def sign_in(self, data, **_):
        token, user = auth.login(self.conn, data.get("email"), data.get("password"))
        secure = "; Secure" if os.environ.get("TEAMHUB_SECURE_COOKIE") == "1" else ""
        return 200, [("Set-Cookie", f"session={token}; HttpOnly; SameSite=Lax; Path=/{secure}")], \
            {"user": auth.public(user)}

    def sign_out(self, token, **_):
        auth.logout(self.conn, token)
        return 200, [("Set-Cookie", "session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")], {"ok": True}

    def me(self, user, **_):
        return 200, [], {"user": auth.public(user),
                         "unread_notifications": notifications.unread_count(self.conn, user)}

    def create_user(self, user, data, **_):
        new = auth.create_user(self.conn, data.get("email"), data.get("name"), data.get("password"),
                               data.get("role", "member"), bool(data.get("can_approve")), acting=user)
        return 201, [], {"user": auth.public(new)}

    def notification_settings(self, user, data, **_):
        return 200, [], notifications.set_preferences(self.conn, user, data.get("email"), data.get("push"))

    # tasks
    def list_tasks(self, query, **_):
        return 200, [], {"tasks": tasks.list_tasks(self.conn, query.get("status"), query.get("assignee"))}

    def create_task(self, user, data, **_):
        return 201, [], {"task": tasks.create_task(self.conn, user, data.get("title"), data.get("assignee_id"),
                                                   data.get("due_on"))}

    def update_task(self, user, params, data, **_):
        task = None
        if "assignee_id" in data:
            task = tasks.assign_task(self.conn, user, params["id"], data["assignee_id"])
        if "status" in data:
            task = tasks.move_task(self.conn, user, params["id"], data["status"])
        if task is None:
            raise Invalid("send status and/or assignee_id")
        return 200, [], {"task": task}

    # approvals
    def request_approval(self, user, params, data, **_):
        return 201, [], {"approval": approvals.request_approval(self.conn, user, params["id"], data.get("note"))}

    def list_approvals(self, query, **_):
        return 200, [], {"approvals": approvals.list_approvals(self.conn, query.get("status"))}

    def decide(self, user, params, data, **_):
        return 200, [], {"approval": approvals.decide(self.conn, user, params["id"], data.get("decision"),
                                                      data.get("note"))}

    # comments
    def thread(self, params, **_):
        return 200, [], {"comments": comments.thread(self.conn, params["kind"][:-1], params["id"])}

    def comment(self, user, params, data, **_):
        return 201, [], {"comment": comments.add_comment(self.conn, user, params["kind"][:-1], params["id"],
                                                         data.get("body"), data.get("parent_id"))}

    # notifications and dashboard
    def list_notifications(self, user, query, **_):
        return 200, [], {"notifications": notifications.list_for(self.conn, user, query.get("unread") == "1")}

    def read_notification(self, user, params, **_):
        return 200, [], notifications.mark_read(self.conn, user, params["id"])

    def subscribe_push(self, user, data, **_):
        return 201, [], {"subscription": notifications.subscribe_push(self.conn, user, data.get("endpoint"))}

    def dashboard(self, user, query, **_):
        return 200, [], dashboard.workload(self.conn, user, query.get("today"))


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def _run(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > 1_000_000:
                status, headers, payload = 413, [], {"error": {"code": "too_large", "message": "request too large"}}
            else:
                body = self.rfile.read(length) if length else b""
                status, headers, payload = app.handle(self.command, self.path, body, self.headers.get("Cookie", ""))
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            for name, value in headers:
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _run

        def log_message(self, *args):  # no request logging: paths can hold ids
            pass

    return Handler


def serve(conn, host="127.0.0.1", port=8000):
    return ThreadingHTTPServer((host, port), make_handler(App(conn)))
