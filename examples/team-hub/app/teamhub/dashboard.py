"""Workload dashboard (M14), rebuilt from Pulse's public description."""

from datetime import datetime, timezone

from .auth import require
from .tasks import STATUSES


def workload(conn, user, today=None):
    require(user, "dashboard.view")
    today = today or datetime.now(timezone.utc).date().isoformat()  # D06: overdue is judged in UTC
    by_status = {s: 0 for s in STATUSES}
    for r in conn.execute("select status, count(*) n from tasks group by status").fetchall():
        by_status[r["status"]] = r["n"]
    people = conn.execute(
        "select u.id, u.name, count(t.id) open from users u "
        "left join tasks t on t.assignee_id = u.id and t.status != 'done' "
        "group by u.id order by open desc, u.name").fetchall()
    overdue = conn.execute("select count(*) from tasks where status != 'done' and due_on is not null "
                           "and due_on < ?", (today,)).fetchone()[0]
    pending = conn.execute("select count(*) from approvals where status = 'pending'").fetchone()[0]
    return {"tasks_by_status": by_status,
            "open_by_person": [{"user_id": p["id"], "name": p["name"], "open": p["open"]} for p in people],
            "overdue": overdue, "pending_approvals": pending}
