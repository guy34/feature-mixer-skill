class ApiError(Exception):
    def __init__(self, source, status, message):
        super().__init__(f"{source} {status}: {message}")
        self.source, self.status, self.message = source, status, message


class NotFound(ApiError):
    pass


class NotSupported(Exception):
    pass


class Client:
    def __init__(self, transport, a_token, b_key, sleep):
        self.t, self.sleep = transport, sleep
        self.headers = {"A": {"Authorization": f"Bearer {a_token}"}, "B": {"X-Api-Key": b_key}}

    def _call(self, source, method, url):
        for attempt in range(4):
            r = self.t.request(method, url, self.headers[source])
            if r.status == 429 and attempt < 3:
                self.sleep(int(r.headers.get("Retry-After", "1")))
                continue
            break
        if r.status >= 400:
            body = r.json() or {}
            msg = body.get("error") if source == "A" else body.get("title")
            raise (NotFound if r.status == 404 else ApiError)(source, r.status, msg or "error")
        return r.json()

    def list_all(self):
        out, off = [], 0
        while True:
            page = self._call("A", "GET", f"/v1/contacts?offset={off}&limit=2")
            out += [{"source": "A", "id": x["id"], "name": x["name"]} for x in page["items"]]
            off += len(page["items"])
            if not page["items"] or off >= page["total"]:
                break
        cursor = ""
        while True:
            page = self._call("B", "GET", "/v2/people" + (f"?cursor={cursor}" if cursor else ""))
            out += [{"source": "B", "id": x["id"], "name": x.get("name") or x.get("full_name")} for x in page["data"]]
            cursor = page.get("next_cursor")
            if not cursor:
                break
        return out

    def get(self, source, cid):
        url = f"/v1/contacts/{cid}" if source == "A" else f"/v2/people/{cid}"
        x = self._call(source, "GET", url)
        return {"source": source, "id": x["id"], "name": x.get("name") or x.get("full_name")}

    def delete(self, source, cid):
        if source == "B":
            raise NotSupported("Addressly has no delete endpoint")
        self._call("A", "DELETE", f"/v1/contacts/{cid}")


def create_client(transport, a_token, b_key, sleep):
    return Client(transport, a_token, b_key, sleep)
