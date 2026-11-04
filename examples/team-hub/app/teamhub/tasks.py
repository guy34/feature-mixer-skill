"""Task board and assignment (M04, M05)."""

from datetime import date

from .auth import can, get_user, require
from .db import new_id, now
from .errors import Forbidden, Invalid, NotFound
from .notifications import notify

STATUSES = ("todo", "doing", "done")

# Other modules can veto a status change (approvals use this; see the
# compatibility decision on closing tasks with pending approvals).
_status_guards = []


def register_status_guard(fn):
    if fn not in _status_guards:
        _status_guards.append(fn)


def _row(conn, task_id):
    row = conn.execute("select * from tasks where id = ?", (task_id,)).fetchone()
    if not row:
        raise NotFound("no such task")
    return row


def to_dict(row):
    return {k: row[k] for k in ("id", "title", "status", "assignee_id", "created_by", "due_on",
                                "created_at", "updated_at")}


def get_task(conn, task_id):
    return to_dict(_row(conn, task_id))


def list_tasks(conn, status=None, assignee_id=None):
    sql, args = "select * from tasks where 1 = 1", []
    if status:
        if status not in STATUSES:
            raise Invalid(f"status must be one of {', '.join(STATUSES)}")
        sql += " and status = ?"
        args.append(status)
    if assignee_id:
        sql += " and assignee_id = ?"
        args.append(assignee_id)
    return [to_dict(r) for r in conn.execute(sql + " order by created_at, rowid", args).fetchall()]


def _check_assignee(conn, assignee_id):
    if assignee_id is None:
        return None
    try:
        return get_user(conn, assignee_id)
    except NotFound:
        raise Invalid("the assignee does not exist")


def _notify_assignee(conn, task_id, title, assignee, actor):
    if assignee is not None and assignee["id"] != actor["id"]:
        notify(conn, assignee["id"], "task.assigned", f'{actor["name"]} assigned you "{title}"',
               f"task.assigned:{task_id}:{assignee['id']}")


def create_task(conn, user, title, assignee_id=None, due_on=None):
    require(user, "task.create")
    title = (title or "").strip()
    if not 1 <= len(title) <= 200:
        raise Invalid("title must be 1 to 200 characters")
    if due_on is not None:
        try:
            date.fromisoformat(due_on)
        except (TypeError, ValueError):
            raise Invalid("due_on must be a date like 2026-12-31")
    assignee = _check_assignee(conn, assignee_id)
    tid, ts = new_id(), now()
    conn.execute(
        "insert into tasks (id, title, assignee_id, created_by, due_on, created_at, updated_at) "
        "values (?,?,?,?,?,?,?)",
        (tid, title, assignee_id, user["id"], due_on, ts, ts),
    )
    _notify_assignee(conn, tid, title, assignee, user)
    conn.commit()
    return get_task(conn, tid)


def _may_change(user, task):
    return user["id"] in (task["created_by"], task["assignee_id"]) or can(user, "task.manage_any")


def move_task(conn, user, task_id, status):
    if status not in STATUSES:
        raise Invalid(f"status must be one of {', '.join(STATUSES)}")
    task = _row(conn, task_id)
    if not _may_change(user, task):
        raise Forbidden("only the creator, the assignee, an owner or an admin can move this task")
    for guard in _status_guards:
        guard(conn, task, status)
    conn.execute("update tasks set status = ?, updated_at = ? where id = ?", (status, now(), task_id))
    conn.commit()
    return get_task(conn, task_id)


def assign_task(conn, user, task_id, assignee_id):
    task = _row(conn, task_id)
    if user["id"] != task["created_by"] and not can(user, "task.manage_any"):
        raise Forbidden("only the creator, an owner or an admin can assign this task")
    assignee = _check_assignee(conn, assignee_id)
    conn.execute("update tasks set assignee_id = ?, updated_at = ? where id = ?", (assignee_id, now(), task_id))
    _notify_assignee(conn, task_id, task["title"], assignee, user)
    conn.commit()
    return get_task(conn, task_id)
