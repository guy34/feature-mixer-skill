import secrets


class App:
    def __init__(self, clock):
        self.clock, self.files, self.links, self.notes, self.gone = clock, {}, {}, {}, set()

    def upload(self, user, name, data):
        fid = "f_" + secrets.token_hex(12)
        self.files[fid] = {"owner": user, "name": name, "data": bytes(data)}
        return fid

    def _owned(self, user, fid):
        if fid not in self.files:
            raise KeyError(fid)
        if self.files[fid]["owner"] != user:
            raise PermissionError("not your file")
        return self.files[fid]

    def preview(self, user, fid):
        return self._owned(user, fid)["data"][:64]

    def share(self, user, fid, seconds):
        self._owned(user, fid)
        t = secrets.token_urlsafe(24)
        self.links[t] = {"file": fid, "expires": self.clock() + float(seconds)}
        return t

    def open_link(self, token):
        link = self.links.get(token)
        if link is None or self.clock() >= link["expires"] or link["file"] not in self.files:
            raise PermissionError("link expired, revoked or unknown")
        return self.files[link["file"]]["data"][:64]

    def delete(self, user, fid):
        self._owned(user, fid)
        del self.files[fid]
        self.gone.add(fid)
        for t in [t for t, l in self.links.items() if l["file"] == fid]:
            del self.links[t]

    def attach(self, user, note, fid):
        self._owned(user, fid)
        self.notes.setdefault((user, note), []).append(fid)

    def attachments(self, user, note):
        return [{"file": f, "status": "ok" if f in self.files else "deleted"} for f in self.notes.get((user, note), [])]


def create_app(clock):
    return App(clock)
