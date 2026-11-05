import json


class Response:
    def __init__(self, status, body=None, headers=None):
        self.status, self.headers = status, headers or {}
        self.text = json.dumps(body) if body is not None else ""

    def json(self):
        return json.loads(self.text) if self.text else None


class MockTransport:
    """Both APIs in memory. request(method, url, headers) -> Response. Records every call."""
    ALLOWED = {("GET", "/v1/contacts"), ("GET", "/v1/contacts/{id}"), ("DELETE", "/v1/contacts/{id}"),
               ("GET", "/v2/people"), ("GET", "/v2/people/{id}")}

    def __init__(self, token="tok", key="key", a_count=5, b_count=5, rate_limit_once=True):
        self.token, self.key, self.calls = token, key, []
        self.a = {str(i): {"id": str(i), "name": f"A person {i}"} for i in range(1, a_count + 1)}
        self.b = [{"id": f"b{i}", "name": f"B person {i}"} for i in range(1, b_count + 1)]
        self.limited = rate_limit_once

    def _shape(self, method, path):
        parts = path.strip("/").split("/")
        return method, "/" + "/".join(parts[:2]) + ("/{id}" if len(parts) > 2 else "")

    def request(self, method, url, headers=None):
        headers = headers or {}
        path, _, query = url.partition("?")
        q = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
        self.calls.append(self._shape(method, path))
        if path.startswith("/v1/"):
            if headers.get("Authorization") != f"Bearer {self.token}":
                return Response(401, {"error": "bad token"})
            if method == "GET" and path == "/v1/contacts":
                off, lim = int(q.get("offset", 0)), min(int(q.get("limit", 2)), 2)
                items = list(self.a.values())
                return Response(200, {"items": items[off:off + lim], "total": len(items)})
            cid = path.rsplit("/", 1)[-1]
            if cid not in self.a:
                return Response(404, {"error": "not found"})
            if method == "DELETE":
                del self.a[cid]
                return Response(204)
            return Response(200, self.a[cid])
        if path.startswith("/v2/"):
            if headers.get("X-Api-Key") != self.key:
                return Response(401, {"title": "bad key", "status": 401})
            if self.limited:
                self.limited = False
                return Response(429, {"title": "slow down", "status": 429}, {"Retry-After": "7"})
            if method == "GET" and path == "/v2/people":
                start = int(q.get("cursor") or 0)
                page = self.b[start:start + 2]
                nxt = start + 2 if start + 2 < len(self.b) else None
                return Response(200, {"data": page, "next_cursor": None if nxt is None else str(nxt)})
            pid = path.rsplit("/", 1)[-1]
            hit = next((p for p in self.b if p["id"] == pid), None)
            if method != "GET":
                return Response(405, {"title": "method not allowed", "status": 405})
            return Response(200, hit) if hit else Response(404, {"title": "no such person", "status": 404})
        return Response(404, {"error": "no such endpoint"})
