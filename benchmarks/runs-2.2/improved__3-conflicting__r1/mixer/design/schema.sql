-- Unified Community Forum: first migration (PostgreSQL 16). Plan only: not run.
create extension if not exists pgcrypto;

create table users (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  display_name text not null,
  role text not null default 'member' check (role in ('member', 'moderator')),
  password_hash text,
  legacy_id integer,
  imported_from text check (imported_from in ('A', 'B')),
  created_at timestamptz not null default now()
);
create unique index users_email_lower on users (lower(email));
create unique index users_legacy on users (imported_from, legacy_id) where legacy_id is not null;

create table sessions (
  sid text primary key,
  sess jsonb not null,
  expire timestamptz not null
);
create index sessions_expire on sessions (expire);

create table posts (
  id uuid primary key default gen_random_uuid(),
  author_id uuid references users(id) on delete restrict,
  body text not null check (length(body) between 1 and 10000),
  status text not null default 'pending' check (status in ('pending', 'published', 'rejected')),
  created_at timestamptz not null default now(),
  legacy_id integer,
  imported_from text check (imported_from in ('A', 'B')),
  check (author_id is not null or imported_from = 'B')
);
create index posts_status_created on posts (status, created_at desc, id desc);
create index posts_author on posts (author_id);
create unique index posts_legacy on posts (imported_from, legacy_id) where legacy_id is not null;

create table moderation_decisions (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null unique references posts(id) on delete cascade,
  moderator_id uuid not null references users(id) on delete restrict,
  decision text not null check (decision in ('published', 'rejected')),
  decided_at timestamptz not null default now()
);
create index moderation_decisions_moderator on moderation_decisions (moderator_id);
