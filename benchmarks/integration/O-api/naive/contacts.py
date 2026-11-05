# Naive: first page only, no retry, errors passed through as-is, and a delete for B invented by symmetry.
class ApiError(Exception):
    def __init__(self, source=None, status=None, message=""):
        super().__init__(message); self.source, self.status = source, status


class NotFound(ApiError):
    pass


class NotSupported(Exception):
    pass


class Client:
    def __init__(self, transport, a_token, b_key, sleep):
        self.t = transport
        self.h = {"A": {"Authorization": f"Bearer {a_token}"}, "B": {"X-Api-Key": b_key}}

    def list_all(self):
        a = self.t.request("GET", "/v1/contacts", self.h["A"]).json()["items"]
        b = self.t.request("GET", "/v2/people", self.h["B"]).json() or {}
        return [{"source": "A", **x} for x in a] + [{"source": "B", **x} for x in b.get("data", [])]

    def get(self, source, cid):
        url = f"/v1/contacts/{cid}" if source == "A" else f"/v2/people/{cid}"
        r = self.t.request("GET", url, self.h[source])
        if r.status == 404:
            raise NotFound(source, 404, "nf")
        if r.status >= 400:
            raise Exception(r.text)
        return {"source": source, **r.json()}

    def delete(self, source, cid):
        url = f"/v1/contacts/{cid}" if source == "A" else f"/v2/people/{cid}"
        self.t.request("DELETE", url, self.h[source])


def create_client(transport, a_token, b_key, sleep):
    return Client(transport, a_token, b_key, sleep)
