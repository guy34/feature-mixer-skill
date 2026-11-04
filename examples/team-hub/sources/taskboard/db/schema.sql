create table users (
  id uuid primary key,
  email text not null unique,
  name text not null,
  password_hash text not null,
  role text not null check (role in ('owner', 'member')),
  created_at timestamptz not null default now()
);

create table tasks (
  id uuid primary key,
  title text not null,
  status text not null default 'todo' check (status in ('todo', 'doing', 'done')),
  assignee_id uuid references users(id) on delete set null,
  created_by uuid not null references users(id),
  due_on date,
  created_at timestamptz not null default now()
);

create table comments (
  id uuid primary key,
  task_id uuid not null references tasks(id) on delete cascade,
  author_id uuid not null references users(id),
  body text not null,
  created_at timestamptz not null default now()
);

create table notifications (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  message text not null,
  read_at timestamptz,
  created_at timestamptz not null default now()
);

create table share_links (
  token text primary key,
  board_owner uuid not null references users(id),
  can_edit boolean not null default true
);
