"""One notification engine with three channels (M10 in-app, M11 email, M12 push).

Every event creates one notification (in-app, always). The user's
preferences decide which extra channels deliver it; each delivery is queued
for a sender (an email provider, a web push service). A dedupe key makes
every event notify at most once.
"""

from .db import new_id, now
from .errors import Conflict, Invalid, NotFound

CHANNELS = ("in-app", "email", "push")


def notify(conn, user_id, event, message, dedupe_key):
    """Record a notification and queue its deliveries. The caller commits."""
    existing = conn.execute("select id from notifications where dedupe_key = ?", (dedupe_key,)).fetchone()
    if existing:
        return existing["id"]
    user = conn.execute("select * from users where id = ?", (user_id,)).fetchone()
    if not user:
        raise NotFound("no such user")
    nid, ts = new_id(), now()
    conn.execute(
        "insert into notifications (id, user_id, event, message, dedupe_key, created_at) values (?,?,?,?,?,?)",
        (nid, user_id, event, message, dedupe_key, ts),
    )
    if user["notify_email"]:
        _queue(conn, nid, "email", user["email"], ts)
    if user["notify_push"]:
        for sub in conn.execute("select endpoint from push_subscriptions where user_id = ?", (user_id,)).fetchall():
            _queue(conn, nid, "push", sub["endpoint"], ts)
    return nid


def _queue(conn, nid, channel, target, ts):
    conn.execute("insert into deliveries (id, notification_id, channel, target, created_at) values (?,?,?,?,?)",
                 (new_id(), nid, channel, target, ts))


def list_for(conn, user, unread_only=False):
    sql = "select * from notifications where user_id = ?"
    if unread_only:
        sql += " and read_at is null"
    rows = conn.execute(sql + " order by created_at desc, rowid desc", (user["id"],)).fetchall()
    return [{"id": r["id"], "event": r["event"], "message": r["message"], "read": r["read_at"] is not None,
             "created_at": r["created_at"]} for r in rows]


def unread_count(conn, user):
    return conn.execute("select count(*) from notifications where user_id = ? and read_at is null",
                        (user["id"],)).fetchone()[0]


def mark_read(conn, user, notification_id):
    row = conn.execute("select * from notifications where id = ? and user_id = ?",
                       (notification_id, user["id"])).fetchone()
    if not row:
        raise NotFound("no such notification")  # someone else's looks the same as a missing one
    if row["read_at"] is None:
        conn.execute("update notifications set read_at = ? where id = ?", (now(), notification_id))
        conn.commit()
    return {"id": notification_id, "read": True}


def set_preferences(conn, user, email=None, push=None):
    for column, value in (("notify_email", email), ("notify_push", push)):
        if value is not None:
            if not isinstance(value, bool):
                raise Invalid(f"{column.replace('notify_', '')} must be true or false")
            conn.execute(f"update users set {column} = ? where id = ?", (int(value), user["id"]))
    conn.commit()
    row = conn.execute("select notify_email, notify_push from users where id = ?", (user["id"],)).fetchone()
    return {"email": bool(row["notify_email"]), "push": bool(row["notify_push"])}


def subscribe_push(conn, user, endpoint):
    """Opt this browser in to push (Pulse's documented rule: per browser, HTTPS only)."""
    endpoint = (endpoint or "").strip()
    if not endpoint.startswith("https://") or len(endpoint) > 2000:
        raise Invalid("a push endpoint must be an https:// URL")
    if conn.execute("select 1 from push_subscriptions where endpoint = ?", (endpoint,)).fetchone():
        raise Conflict("this browser is already subscribed")
    sid = new_id()
    conn.execute("insert into push_subscriptions (id, user_id, endpoint, created_at) values (?,?,?,?)",
                 (sid, user["id"], endpoint, now()))
    conn.execute("update users set notify_push = 1 where id = ?", (user["id"],))
    conn.commit()
    return {"id": sid, "endpoint": endpoint}


def outbox(conn, channel=None):
    """Deliveries waiting for a sender."""
    sql = "select d.*, n.event, n.message from deliveries d join notifications n on n.id = d.notification_id " \
          "where d.status = 'queued'"
    args = ()
    if channel:
        sql += " and d.channel = ?"
        args = (channel,)
    return [dict(r) for r in conn.execute(sql + " order by d.created_at, d.rowid", args).fetchall()]
