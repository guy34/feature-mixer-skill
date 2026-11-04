"""Sharing: create, open and revoke share links with expiry and an optional password.

Adapted from ShareLink (C, user's own code): random 16-byte tokens, default 24 h expiry,
unknown and expired links look the same. Changes: links are stored in SQLite and tied to a
file the caller owns; passwords use salted PBKDF2; only the file's owner may revoke.
"""

from .accounts import current_user, iso
from .config import DEFAULT_LINK_HOURS
from .core.http import HTTPError, json_response, no_content
from .core.security import hash_password, new_token, verify_password
from .files import content_response, get_owned_file
from .preview import preview_row


def create_link(ctx, req, file_id):
    user = current_user(ctx, req)
    data = req.json()
    get_owned_file(ctx, user, file_id)
    hours = data.get("expires_in_hours", DEFAULT_LINK_HOURS)
    if isinstance(hours, bool) or not isinstance(hours, (int, float)) or not hours > 0 or hours != hours:
        raise HTTPError(400, "invalid_expiry", "expires_in_hours must be a positive number")
    password = data.get("password")
    if password is not None and (not isinstance(password, str) or not 1 <= len(password) <= 256):
        raise HTTPError(400, "invalid_password", "password must be 1-256 characters")
    token = new_token()
    now = ctx.clock()
    expires_at = now + hours * 3600
    pw_hash = hash_password(password, ctx.config.pbkdf2_iterations) if password else None
    ctx.db.execute("INSERT INTO share_links (token, file_id, expires_at, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                   (token, file_id, expires_at, pw_hash, iso(now)))
    ctx.db.commit()
    return json_response(201, {"token": token, "url": f"/s/{token}", "expires_at": expires_at,
                               "has_password": pw_hash is not None})


def open_link(ctx, req, token):
    """The shared file for a valid token and password, else 404 (unknown/expired) or 403 (password)."""
    row = ctx.db.execute(
        "SELECT l.expires_at, l.password_hash, f.* FROM share_links l JOIN files f ON f.id = l.file_id "
        "WHERE l.token = ?", (token,)).fetchone()
    if not row or row["expires_at"] < ctx.clock():
        raise HTTPError(404, "not_found", "link expired or unknown")
    if row["password_hash"]:
        given = req.header("X-Link-Password")
        if not given:
            raise HTTPError(403, "password_required", "this link needs a password")
        if not verify_password(given, row["password_hash"]):
            raise HTTPError(403, "wrong_password", "wrong password")
    return row


def shared_file(ctx, req, token):
    row = open_link(ctx, req, token)
    return json_response(200, {"name": row["name"], "size": row["size"], "content_type": row["content_type"],
                               "preview": preview_row(ctx, row, f"/api/share/{token}/content")})


def shared_content(ctx, req, token):
    return content_response(ctx, open_link(ctx, req, token))


def revoke_link(ctx, req, token):
    user = current_user(ctx, req)
    row = ctx.db.execute("SELECT l.token FROM share_links l JOIN files f ON f.id = l.file_id "
                         "WHERE l.token = ? AND f.owner_id = ?", (token, user["id"])).fetchone()
    if not row:
        raise HTTPError(404, "not_found", "no such link")
    ctx.db.execute("DELETE FROM share_links WHERE token = ?", (token,))
    ctx.db.commit()
    return no_content()
