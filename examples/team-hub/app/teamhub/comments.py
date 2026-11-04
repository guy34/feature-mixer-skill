"""Threaded comments on tasks and approvals (M07)."""

from .auth import require
from .db import new_id, now
from .errors import Invalid, NotFound
from .notifications import notify

SUBJECTS = {"task": "tasks", "approval": "approvals"}


def _subject_exists(conn, subject_type, subject_id):
    if subject_type not in SUBJECTS:
        raise Invalid("comments can be added to a task or an approval")
    table = SUBJECTS[subject_type]
    if not conn.execute(f"select 1 from {table} where id = ?", (subject_id,)).fetchone():
        raise NotFound(f"no such {subject_type}")


def add_comment(conn, user, subject_type, subject_id, body, parent_id=None):
    require(user, "comment.create")
    _subject_exists(conn, subject_type, subject_id)
    body = (body or "").strip()
    if not 1 <= len(body) <= 5000:
        raise Invalid("a comment must be 1 to 5000 characters")
    parent = None
    if parent_id is not None:
        parent = conn.execute("select * from comments where id = ?", (parent_id,)).fetchone()
        if not parent or (parent["subject_type"], parent["subject_id"]) != (subject_type, subject_id):
            raise Invalid("a reply must answer a comment on the same item")
    cid = new_id()
    conn.execute("insert into comments (id, subject_type, subject_id, parent_id, author_id, body, created_at) "
                 "values (?,?,?,?,?,?,?)", (cid, subject_type, subject_id, parent_id, user["id"], body, now()))
    if parent is not None and parent["author_id"] != user["id"]:
        notify(conn, parent["author_id"], "comment.reply", f'{user["name"]} replied to your comment',
               f"comment.reply:{cid}")
    conn.commit()
    return {"id": cid, "parent_id": parent_id, "author_id": user["id"], "body": body}


def thread(conn, subject_type, subject_id):
    """Comments as a tree: each has its replies."""
    _subject_exists(conn, subject_type, subject_id)
    rows = conn.execute("select * from comments where subject_type = ? and subject_id = ? "
                        "order by created_at, rowid", (subject_type, subject_id)).fetchall()
    nodes = {r["id"]: {"id": r["id"], "author_id": r["author_id"], "body": r["body"],
                       "created_at": r["created_at"], "replies": []} for r in rows}
    roots = []
    for r in rows:
        (nodes[r["parent_id"]]["replies"] if r["parent_id"] else roots).append(nodes[r["id"]])
    return roots
