# A plausible naive merge: accounts joined by email whatever the provider says; roles copied from the
# sources; the role check from C was lost in the merge.
import secrets


class AuthError(Exception):
    pass


class App:
    def __init__(self):
        self.users, self.sessions = {}, {}

    def _by_email(self, email):
        return next((u for u in self.users.values() if u["email"].lower() == email.lower()), None)

    def register_password(self, email, password):
        uid = len(self.users) + 1
        self.users[uid] = {"id": uid, "email": email, "pw": password, "role": "editor"}
        return uid

    def bootstrap_admin(self, email, password):
        uid = self.register_password(email, password)
        self.users[uid]["role"] = "admin"
        return uid

    def login_password(self, email, password):
        u = self._by_email(email)
        if not u or u["pw"] != password:
            raise AuthError("bad credentials")
        t = secrets.token_hex(8); self.sessions[t] = u["id"]; return t

    def login_oauth(self, provider, subject, email, email_verified):
        u = self._by_email(email) or self.users.setdefault(len(self.users) + 1, {
            "id": len(self.users) + 1, "email": email, "pw": None, "role": "viewer"})
        t = secrets.token_hex(8); self.sessions[t] = u["id"]; return t

    def whoami(self, token):
        if token not in self.sessions:
            raise AuthError("no")
        u = self.users[self.sessions[token]]
        return {"user_id": u["id"], "email": u["email"], "role": u["role"]}

    def logout(self, token):
        self.sessions.pop(token, None)

    def set_role(self, token, user_id, role):
        self.whoami(token)
        self.users[user_id]["role"] = role

    def map_source_role(self, source_app, role):
        return {"user": "editor", "member": "viewer"}.get(role, role)


def create_app():
    return App()
