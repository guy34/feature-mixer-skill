class Locked(Exception):
    pass


class App:
    def __init__(self):
        self.users, self.docs, self.log = {}, {}, {}

    def add_user(self, user_id, role):
        self.users[user_id] = role

    def create(self, user_id, text):
        i = len(self.docs) + 1
        self.docs[i] = {"text": text, "status": "draft", "owner": user_id}
        self.log[i] = [{"user": user_id, "action": "create", "reason": None}]
        return i

    def edit(self, user_id, doc_id, text, reason=None):
        d = self.docs[doc_id]
        admin = self.users.get(user_id) == "admin"
        if d["status"] == "draft":
            if d["owner"] != user_id:
                raise PermissionError("only the author edits a draft")
            action = "edit"
        elif admin:
            if not (reason or "").strip():
                raise Locked("an override needs a reason")
            action = "override"
        elif d["owner"] == user_id:
            raise Locked("submitted documents are locked")
        else:
            raise PermissionError("not your document")
        d["text"] = text
        self.log[doc_id].append({"user": user_id, "action": action, "reason": reason})

    def submit(self, user_id, doc_id):
        d = self.docs[doc_id]
        if d["owner"] != user_id:
            raise PermissionError("only the author submits")
        d["status"] = "submitted"
        self.log[doc_id].append({"user": user_id, "action": "submit", "reason": None})

    def get(self, doc_id):
        return dict(self.docs[doc_id])

    def audit(self, doc_id):
        return list(self.log[doc_id])


def create_app():
    return App()
