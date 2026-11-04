"""Files: upload, list, delete and serve an owner's files.

Adapted from Uploader (A, user's own code): the 10 MB limit and owner scoping of
upload/list/delete, now on SQLite with the owner taken from the session.
"""

import mimetypes
import uuid

from .accounts import current_user, iso
from .config import MAX_UPLOAD_BYTES
from .core.http import HTTPError, Response, json_response, no_content

INLINE_TYPES = {"image/png", "image/jpeg", "image/gif"}


def _public(row):
    return {"id": row["id"], "name": row["name"], "size": row["size"],
            "content_type": row["content_type"], "created_at": row["created_at"]}


def _clean_name(raw):
    name = (raw or "").strip()
    if not name or len(name) > 255 or any(c in name for c in "/\\\x00") or name in (".", ".."):
        raise HTTPError(400, "invalid_name", "give a file name of 1-255 characters without slashes")
    return name


def get_owned_file(ctx, user, file_id):
    """The one ownership check: the file if this user owns it, else 404 (never reveal others' files)."""
    row = ctx.db.execute("SELECT * FROM files WHERE id = ? AND owner_id = ?", (file_id, user["id"])).fetchone()
    if not row:
        raise HTTPError(404, "not_found", "no such file")
    return row


def read_content(ctx, file_id):
    return ctx.db.execute("SELECT data FROM file_content WHERE file_id = ?", (file_id,)).fetchone()["data"]


def upload(ctx, req):
    user = current_user(ctx, req)
    name = _clean_name(req.query.get("name"))
    length = req.content_length()
    if length is None:
        raise HTTPError(411, "length_required", "send Content-Length with the upload")
    if length > MAX_UPLOAD_BYTES:  # checked before reading the body
        raise HTTPError(413, "file_too_large", "file too large (limit 10 MB)")
    data = req.body()
    if len(data) != length:
        raise HTTPError(400, "incomplete_body", "upload ended early")
    file_id = uuid.uuid4().hex
    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
    created = iso(ctx.clock())
    ctx.db.execute("INSERT INTO files (id, owner_id, name, size, content_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (file_id, user["id"], name, len(data), ctype, created))
    ctx.db.execute("INSERT INTO file_content (file_id, data) VALUES (?, ?)", (file_id, data))
    ctx.db.commit()
    return json_response(201, {"id": file_id, "name": name, "size": len(data), "content_type": ctype, "created_at": created})


def list_files(ctx, req):
    user = current_user(ctx, req)
    rows = ctx.db.execute("SELECT * FROM files WHERE owner_id = ? ORDER BY created_at DESC, rowid DESC",
                          (user["id"],)).fetchall()
    return json_response(200, {"files": [_public(r) for r in rows]})


def delete_file(ctx, req, file_id):
    user = current_user(ctx, req)
    get_owned_file(ctx, user, file_id)
    ctx.db.execute("DELETE FROM files WHERE id = ?", (file_id,))  # cascades to content and share links
    ctx.db.commit()
    return no_content()


def content_response(ctx, row):
    """Serve a file's bytes; png/jpg/gif inline (image preview), everything else as a download."""
    ctype = row["content_type"]
    disposition = "inline" if ctype in INLINE_TYPES else "attachment"
    safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in row["name"])
    return Response(200, read_content(ctx, row["id"]), ctype,
                    [("Content-Disposition", f'{disposition}; filename="{safe}"'), ("Cache-Control", "private, no-store")])


def file_content(ctx, req, file_id):
    user = current_user(ctx, req)
    return content_response(ctx, get_owned_file(ctx, user, file_id))
