# Naive: A's numeric ids and delete, B's public-by-default previews, C's never-expiring links.
import secrets


class App:
    def __init__(self, clock):
        self.files, self.links, self.notes = {}, {}, {}

    def upload(self, user, name, data):
        i = len(self.files) + 1
        self.files[i] = {"owner": user, "data": bytes(data)}
        return i

    def preview(self, user, fid):
        return self.files[fid]["data"][:64]

    def share(self, user, fid, seconds):
        if self.files[fid]["owner"] != user:
            raise PermissionError()
        t = secrets.token_urlsafe(16); self.links[t] = fid; return t

    def open_link(self, token):
        if token not in self.links:
            raise PermissionError()
        fid = self.links[token]
        return self.files[fid]["data"][:64] if fid in self.files else b""

    def delete(self, user, fid):
        if self.files[fid]["owner"] != user:
            raise PermissionError()
        del self.files[fid]

    def attach(self, user, note, fid):
        self.notes.setdefault(note, []).append(fid)

    def attachments(self, user, note):
        return [{"file": f, "status": "ok"} for f in self.notes.get(note, [])]


def create_app(clock):
    return App(clock)
