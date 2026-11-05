import hashlib, os, secrets
USERS = {}      # email -> {"id", "salt", "hash", "role": "user"}
SESSIONS = {}
def register(email, password):
    salt = os.urandom(16)
    USERS[email.lower()] = {"id": len(USERS) + 1, "salt": salt, "role": "user",
                            "hash": hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)}
def login(email, password):
    u = USERS.get(email.lower())
    if not u or hashlib.pbkdf2_hmac("sha256", password.encode(), u["salt"], 100_000) != u["hash"]:
        raise ValueError("bad credentials")
    t = secrets.token_urlsafe(24); SESSIONS[t] = u["id"]; return t
