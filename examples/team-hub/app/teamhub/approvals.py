"""Approval requests on tasks (M13)."""

from .auth import get_user, require
from .db import new_id, now
from .errors import Conflict, Forbidden, Invalid, NotFound
from .notifications import notify
from .tasks import get_task, register_status_guard

DECISIONS = ("approved", "rejected")


def _pending_for_task(conn, task_id):
    return conn.execute("select * from approvals where task_id = ? and status = 'pending'", (task_id,)).fetchone()


def _guard(conn, task, status):
    """A task with a pending approval cannot be closed (compatibility decision)."""
    if status == "done" and _pending_for_task(conn, task["id"]):
        raise Conflict("this task has a pending approval; it can be closed once the approval is decided")


register_status_guard(_guard)


def to_dict(row):
    return {k: row[k] for k in ("id", "task_id", "requester_id", "approver_id", "status", "note",
                                "created_at", "decided_at")}


def get_approval(conn, approval_id):
    row = conn.execute("select * from approvals where id = ?", (approval_id,)).fetchone()
    if not row:
        raise NotFound("no such approval")
    return to_dict(row)


def list_approvals(conn, status=None):
    if status and status not in ("pending",) + DECISIONS:
        raise Invalid("status must be pending, approved or rejected")
    sql, args = "select * from approvals", ()
    if status:
        sql, args = sql + " where status = ?", (status,)
    return [to_dict(r) for r in conn.execute(sql + " order by created_at, rowid", args).fetchall()]


def request_approval(conn, user, task_id, note=None):
    require(user, "approval.request")
    task = get_task(conn, task_id)
    if _pending_for_task(conn, task_id):
        raise Conflict("this task already has a pending approval")
    if note is not None and len(note) > 2000:
        raise Invalid("note must be at most 2000 characters")
    aid = new_id()
    conn.execute("insert into approvals (id, task_id, requester_id, note, created_at) values (?,?,?,?,?)",
                 (aid, task_id, user["id"], note, now()))
    approvers = conn.execute("select id from users where can_approve = 1 and id != ?", (user["id"],)).fetchall()
    for a in approvers:
        notify(conn, a["id"], "approval.requested", f'{user["name"]} asked for approval on "{task["title"]}"',
               f"approval.requested:{aid}:{a['id']}")
    conn.commit()
    return get_approval(conn, aid)


def decide(conn, user, approval_id, decision, note=None):
    if decision not in DECISIONS:
        raise Invalid("decision must be approved or rejected")
    require(user, "approval.decide")
    row = get_approval(conn, approval_id)
    if row["requester_id"] == user["id"]:
        raise Forbidden("you cannot decide your own request")
    if row["status"] != "pending":
        raise Conflict(f"this approval was already {row['status']}")
    conn.execute("update approvals set status = ?, approver_id = ?, decided_at = ?, note = coalesce(?, note) "
                 "where id = ? and status = 'pending'", (decision, user["id"], now(), note, approval_id))
    task = get_task(conn, row["task_id"])
    requester = get_user(conn, row["requester_id"])
    notify(conn, requester["id"], "approval.decided", f'"{task["title"]}" was {decision} by {user["name"]}',
           f"approval.decided:{approval_id}")
    conn.commit()
    return get_approval(conn, approval_id)
