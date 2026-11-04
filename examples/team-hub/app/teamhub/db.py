"""The unified database schema (architecture.json entities) and connection helper."""

import sqlite3
import uuid
from datetime import datetime, timezone

SCHEMA = """
create table if not exists users (
  id text primary key,
  email text not null unique,
  name text not null,
  password_hash text not null,
  role text not null check (role in ('owner', 'admin', 'member')),
  can_approve integer not null default 0 check (can_approve in (0, 1)),
  notify_email integer not null default 1 check (notify_email in (0, 1)),
  notify_push integer not null default 0 check (notify_push in (0, 1)),
  legacy_id text,
  created_at text not null
);

create table if not exists sessions (
  token text primary key,
  user_id text not null references users(id) on delete cascade,
  last_seen text not null
);

create table if not exists tasks (
  id text primary key,
  title text not null check (length(title) between 1 and 200),
  status text not null default 'todo' check (status in ('todo', 'doing', 'done')),
  assignee_id text references users(id) on delete set null,
  created_by text not null references users(id),
  due_on text,
  created_at text not null,
  updated_at text not null
);
create index if not exists tasks_assignee on tasks (assignee_id, status);

create table if not exists approvals (
  id text primary key,
  task_id text not null references tasks(id) on delete cascade,
  requester_id text not null references users(id),
  approver_id text references users(id),
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  note text,
  created_at text not null,
  decided_at text
);
create index if not exists approvals_task on approvals (task_id, status);

create table if not exists comments (
  id text primary key,
  subject_type text not null check (subject_type in ('task', 'approval')),
  subject_id text not null,
  parent_id text references comments(id) on delete cascade,
  author_id text not null references users(id),
  body text not null check (length(body) between 1 and 5000),
  created_at text not null
);
create index if not exists comments_subject on comments (subject_type, subject_id);

create table if not exists notifications (
  id text primary key,
  user_id text not null references users(id) on delete cascade,
  event text not null,
  message text not null,
  dedupe_key text not null unique,
  read_at text,
  created_at text not null
);
create index if not exists notifications_user on notifications (user_id, read_at);

create table if not exists deliveries (
  id text primary key,
  notification_id text not null references notifications(id) on delete cascade,
  channel text not null check (channel in ('email', 'push')),
  target text not null,
  status text not null default 'queued' check (status in ('queued', 'sent', 'failed')),
  created_at text not null
);

create table if not exists push_subscriptions (
  id text primary key,
  user_id text not null references users(id) on delete cascade,
  endpoint text not null unique,
  created_at text not null
);
"""


def connect(path=":memory:"):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    conn.executescript(SCHEMA)
    return conn


def now(at=None):
    """UTC timestamp as ISO 8601 text (decision D06: times are stored in UTC)."""
    return (at or datetime.now(timezone.utc)).isoformat(timespec="seconds")


def new_id():
    return str(uuid.uuid4())
