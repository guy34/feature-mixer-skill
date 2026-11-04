"""Accounts: register, login, logout and the current user (added; no source had identity)."""

import re
import uuid
from datetime import datetime, timezone

from .core.http import HTTPError, json_response, no_content
from .core.security import hash_password, new_token, verify_password

COOKIE = "fs_session"
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _cookie(ctx, token, max_age):
    parts = [f"{COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Strict", f"Max-Age={max_age}"]
    if ctx.config.secure_cookie:
        parts.append("Secure")
    return ("Set-Cookie", "; ".join(parts))


def _credentials(req):
    data = req.json()
    username, password = data.get("username"), data.get("password")
    if not isinstance(username, str) or not USERNAME_RE.match(username):
        raise HTTPError(400, "invalid_username", "username must be 3-64 letters, digits, '.', '_' or '-'")
    if not isinstance(password, str) or not 8 <= len(password) <= 256:
        raise HTTPError(400, "invalid_password", "password must be 8-256 characters")
    return username, password


def _start_session(ctx, user_id):
    token = new_token()
    seconds = ctx.config.session_hours * 3600
    ctx.db.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                   (token, user_id, ctx.clock() + seconds))
    ctx.db.commit()
    return _cookie(ctx, token, seconds)


def register(ctx, req):
    username, password = _credentials(req)
    if ctx.db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        raise HTTPError(409, "username_taken", "that username is taken")
    user_id = uuid.uuid4().hex
    ctx.db.execute("INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                   (user_id, username, hash_password(password, ctx.config.pbkdf2_iterations), iso(ctx.clock())))
    return json_response(201, {"id": user_id, "username": username}, [_start_session(ctx, user_id)])


def login(ctx, req):
    username, password = _credentials(req)
    row = ctx.db.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPError(401, "bad_credentials", "wrong username or password")
    return json_response(200, {"id": row["id"], "username": username}, [_start_session(ctx, row["id"])])


def logout(ctx, req):
    current_user(ctx, req)
    ctx.db.execute("DELETE FROM sessions WHERE token = ?", (req.cookies.get(COOKIE),))
    ctx.db.commit()
    return no_content([_cookie(ctx, "", 0)])


def current_user(ctx, req):
    """The signed-in user, or 401. Every owner route calls this."""
    token = req.cookies.get(COOKIE)
    if token:
        row = ctx.db.execute(
            "SELECT u.id, u.username, s.expires_at FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ?", (token,)).fetchone()
        if row and row["expires_at"] >= ctx.clock():
            return {"id": row["id"], "username": row["username"]}
    raise HTTPError(401, "not_signed_in", "sign in first")
