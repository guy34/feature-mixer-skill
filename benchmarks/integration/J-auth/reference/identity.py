import hashlib, hmac, os, secrets


class AuthError(Exception):
    pass


ROLE_MAP = {("A", "user"): "editor", ("B", "member"): "viewer",
            ("C", "viewer"): "viewer", ("C", "editor"): "editor", ("C", "admin"): "admin"}


class App:
    def __init__(self):
        self.users, self.by_email, self.links, self.sessions = {}, {}, {}, {}

    def _new(self, email, role, verified):
        uid = secrets.token_hex(8)
        self.users[uid] = {"id": uid, "email": email, "role": role, "verified": verified, "pw": None}
        if verified and email.lower() not in self.by_email:
            self.by_email[email.lower()] = uid
        return uid

    def _session(self, uid):
        t = secrets.token_urlsafe(32)
        self.sessions[t] = uid
        return t

    def register_password(self, email, password):
        if email.lower() in self.by_email:
            raise ValueError("email already registered")
        uid = self._new(email, self.map_source_role("A", "user"), True)
        salt = os.urandom(16)
        self.users[uid]["pw"] = (salt, hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 50_000))
        return uid

    def bootstrap_admin(self, email, password):
        uid = self.register_password(email, password)
        self.users[uid]["role"] = "admin"
        return uid

    def login_password(self, email, password):
        uid = self.by_email.get(email.lower())
        pw = self.users[uid]["pw"] if uid else None
        if not pw or not hmac.compare_digest(pw[1], hashlib.pbkdf2_hmac("sha256", password.encode(), pw[0], 50_000)):
            raise AuthError("bad credentials")
        return self._session(uid)

    def login_oauth(self, provider, subject, email, email_verified):
        key = (provider, subject)
        uid = self.links.get(key)
        if uid is None:
            existing = self.by_email.get(email.lower()) if email_verified else None
            uid = existing or self._new(email, self.map_source_role("B", "member"), bool(email_verified))
            self.links[key] = uid
        return self._session(uid)

    def whoami(self, token):
        uid = self.sessions.get(token)
        if uid is None:
            raise AuthError("not signed in")
        u = self.users[uid]
        return {"user_id": uid, "email": u["email"], "role": u["role"]}

    def logout(self, token):
        self.sessions.pop(token, None)

    def set_role(self, token, user_id, role):
        actor = self.whoami(token)
        if actor["role"] != "admin":
            raise PermissionError("only admins change roles")
        if role not in ("viewer", "editor", "admin"):
            raise ValueError(role)
        self.users[user_id]["role"] = role

    def map_source_role(self, source_app, role):
        return ROLE_MAP[(source_app, role)]


def create_app():
    return App()
