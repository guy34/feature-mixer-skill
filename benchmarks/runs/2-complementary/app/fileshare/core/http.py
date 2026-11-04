"""Minimal WSGI request/response helpers and the one error format {"error": {"code", "message"}}."""

import json
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

STATUS_TEXT = {
    200: "OK", 201: "Created", 204: "No Content", 400: "Bad Request", 401: "Unauthorized",
    403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed", 409: "Conflict",
    411: "Length Required", 413: "Payload Too Large", 500: "Internal Server Error",
}


class HTTPError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class Request:
    def __init__(self, environ):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/") or "/"
        self.query = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True).items()}
        cookie = SimpleCookie()
        try:
            cookie.load(environ.get("HTTP_COOKIE", ""))
        except Exception:
            pass
        self.cookies = {k: m.value for k, m in cookie.items()}
        self._body = None

    def header(self, name):
        return self.environ.get("HTTP_" + name.upper().replace("-", "_"))

    def content_length(self):
        raw = self.environ.get("CONTENT_LENGTH", "")
        if raw in ("", None):
            return None
        try:
            n = int(raw)
        except ValueError:
            raise HTTPError(400, "invalid_length", "Content-Length is not a number")
        if n < 0:
            raise HTTPError(400, "invalid_length", "Content-Length is negative")
        return n

    def body(self, limit=None):
        if self._body is None:
            n = self.content_length() or 0
            if limit is not None and n > limit:
                raise HTTPError(413, "too_large", "request body too large")
            self._body = self.environ["wsgi.input"].read(n) if n else b""
        return self._body

    def json(self):
        raw = self.body(limit=64 * 1024)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise HTTPError(400, "invalid_json", "body is not valid JSON")
        if not isinstance(data, dict):
            raise HTTPError(400, "invalid_json", "body must be a JSON object")
        return data


class Response:
    def __init__(self, status=200, body=b"", content_type="application/json", headers=None):
        self.status = status
        self.body = body
        self.headers = [("Content-Type", content_type)] if content_type else []
        self.headers += list(headers or [])

    def wsgi(self, start_response):
        headers = self.headers + [("Content-Length", str(len(self.body))), ("X-Content-Type-Options", "nosniff")]
        start_response(f"{self.status} {STATUS_TEXT.get(self.status, '')}", headers)
        return [self.body]


def json_response(status, data, headers=None):
    return Response(status, json.dumps(data).encode("utf-8"), "application/json", headers)


def no_content(headers=None):
    return Response(204, b"", None, headers)


def error_response(err):
    return json_response(err.status, {"error": {"code": err.code, "message": err.message}})
