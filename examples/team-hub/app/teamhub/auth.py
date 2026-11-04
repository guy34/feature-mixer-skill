"""Accounts, sessions, roles and permissions (M01, M08, M09; decisions D02 and D04)."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from . import config
from .db import new_id, now
from .errors import Conflict, Forbidden, Invalid, NotFound, Unauthorized

ROLES = ("owner", "admin", "member")

# Who may do what. Approving is a permission (the can_approve flag), not a role.
PERMISSIONS = {
    "task.create": ROLES,
    "task.manage_any": ("owner", "admin"),
    "user.manage": ("owner", "admin"),
    "approval.request": ROLES,
    "comment.create": ROLES,
    "dashboard.view": ROLES,
}


def hash_password(password, salt=None, iterations=None):
    iterations = iterations or config.PASSWORD_ITERATIONS
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(calc.hex(), digest)


def public(user):
    return {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"],
            "can_approve": bool(user["can_approve"])}


def get_user(conn, user_id):
    row = conn.execute("select * from users where id = ?", (user_id,)).fetchone()
    if not row:
        raise NotFound("no such user")
    return row


def create_user(conn, email, name, password, role="member", can_approve=False, acting=None):
    """Create an account. Through the API (acting is a user) only owners and admins may;
    the command line (acting is None) is for whoever runs the server."""
    if acting is not None:
        require(acting, "user.manage")
    email = (email or "").strip().lower()
    name = (name or "").strip()
    if "@" not in email or len(email) > 254:
        raise Invalid("a valid email is required")
    if not 1 <= len(name) <= 80:
        raise Invalid("name must be 1 to 80 characters")
    if len(password or "") < 8:
        raise Invalid("password must be at least 8 characters")
    if role not in ROLES:
        raise Invalid(f"role must be one of {', '.join(ROLES)}")
    if conn.execute("select 1 from users where email = ?", (email,)).fetchone():
        raise Conflict("an account with this email already exists")
    uid = new_id()
    conn.execute(
        "insert into users (id, email, name, password_hash, role, can_approve, created_at) values (?,?,?,?,?,?,?)",
        (uid, email, name, hash_password(password), role, int(bool(can_approve)), now()),
    )
    conn.commit()
    return get_user(conn, uid)


def login(conn, email, password, at=None):
    row = conn.execute("select * from users where email = ?", ((email or "").strip().lower(),)).fetchone()
    if not row or not verify_password(password or "", row["password_hash"]):
        raise Unauthorized("wrong email or password")
    token = secrets.token_urlsafe(32)
    conn.execute("insert into sessions (token, user_id, last_seen) values (?,?,?)", (token, row["id"], now(at)))
    conn.commit()
    return token, row


def user_for_session(conn, token, at=None):
    """The signed-in user; sessions end after SESSION_IDLE_MINUTES without use."""
    if not token:
        raise Unauthorized("sign in first")
    s = conn.execute("select * from sessions where token = ?", (token,)).fetchone()
    if not s:
        raise Unauthorized("sign in first")
    at = at or datetime.now(timezone.utc)
    if at - datetime.fromisoformat(s["last_seen"]) > timedelta(minutes=config.SESSION_IDLE_MINUTES):
        conn.execute("delete from sessions where token = ?", (token,))
        conn.commit()
        raise Unauthorized("session expired, sign in again")
    conn.execute("update sessions set last_seen = ? where token = ?", (now(at), token))
    conn.commit()
    return get_user(conn, s["user_id"])


def logout(conn, token):
    conn.execute("delete from sessions where token = ?", (token,))
    conn.commit()


def can(user, permission):
    if permission == "approval.decide":
        return bool(user["can_approve"])
    return user["role"] in PERMISSIONS.get(permission, ())


def require(user, permission):
    if not can(user, permission):
        raise Forbidden(f"you are not allowed to {permission.replace('.', ' ').replace('_', ' ')}")
