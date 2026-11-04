-- Unified Community Forum schema (PostgreSQL 16). Design artifact; not run.
create table users (
  id uuid primary key default gen_random_uuid(),
  legacy_id integer unique,                         -- OpenForum (B) user id
  email text not null unique,
  display_name text not null,
  role text not null default 'member' check (role in ('member', 'moderator')),
  password_hash text,                               -- argon2id; null for the system account
  password_reset_required boolean not null default false,
  sign_in_disabled boolean not null default false,
  created_at timestamptz not null default now()
);

create table posts (
  id uuid primary key default gen_random_uuid(),
  legacy_id integer unique,                         -- OpenForum (B) post id
  author_id uuid not null references users(id) on delete restrict,
  body text not null check (length(body) between 1 and 10000),
  status text not null default 'pending' check (status in ('pending', 'published', 'rejected')),
  created_at timestamptz not null default now(),
  moderated_by uuid references users(id) on delete set null,
  moderated_at timestamptz,
  check ((status = 'pending') = (moderated_at is null) or legacy_id is not null)
);
create index posts_status_created_idx on posts (status, created_at desc);
create index posts_author_idx on posts (author_id);
create index posts_moderated_by_idx on posts (moderated_by);

create table session (
  sid text primary key,
  sess jsonb not null,
  expire timestamptz not null
);
create index session_expire_idx on session (expire);
