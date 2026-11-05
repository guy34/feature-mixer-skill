# Naive: the three rules "combined": owners may always edit (A), admins may always edit (C), B's lock lost.
class Locked(Exception):
    pass


class App:
    def __init__(self):
        self.users, self.docs = {}, {}

    def add_user(self, user_id, role):
        self.users[user_id] = role

    def create(self, user_id, text):
        i = len(self.docs) + 1
        self.docs[i] = {"text": text, "status": "draft", "owner": user_id}
        return i

    def edit(self, user_id, doc_id, text, reason=None):
        d = self.docs[doc_id]
        if d["owner"] != user_id and self.users.get(user_id) != "admin":
            raise PermissionError("not yours")
        d["text"] = text

    def submit(self, user_id, doc_id):
        self.docs[doc_id]["status"] = "submitted"

    def get(self, doc_id):
        return dict(self.docs[doc_id])

    def audit(self, doc_id):
        return []


def create_app():
    return App()
