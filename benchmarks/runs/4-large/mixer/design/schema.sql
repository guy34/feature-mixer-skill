-- Unified CRM schema (PostgreSQL 16). Django migrations will generate the equivalent.
create table app_user (
  id uuid primary key,
  email text not null,
  name text not null default '',
  password text not null,
  role text not null default 'member' check (role in ('admin', 'member')),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);
create unique index app_user_email_ci on app_user (lower(email));

create table contact (
  id uuid primary key,
  legacy_source text check (legacy_source in ('A')),
  legacy_id text,
  name text not null check (length(name) between 1 and 200),
  email text,
  company text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create unique index contact_email_ci on contact (lower(email)) where email is not null;
create index contact_name_ci on contact (lower(name));
create unique index contact_legacy on contact (legacy_source, legacy_id) where legacy_id is not null;

create table stage (
  id uuid primary key,
  name text not null unique,
  position integer not null,
  outcome text not null default 'open' check (outcome in ('open', 'won', 'lost', 'unspecified')),
  is_active boolean not null default true
);
create index stage_position on stage (position);

create table deal (
  id uuid primary key,
  legacy_source text check (legacy_source in ('A', 'B')),
  legacy_id text,
  contact_id uuid references contact (id) on delete set null,
  title text not null check (length(title) between 1 and 200),
  value_cents integer check (value_cents is null or value_cents >= 0),
  currency text not null default 'USD' check (length(currency) = 3),
  stage_id uuid not null references stage (id) on delete restrict,
  moved_at timestamptz not null default now(),
  owner_id uuid not null references app_user (id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index deal_contact on deal (contact_id);
create index deal_stage on deal (stage_id);
create index deal_owner on deal (owner_id);
create index deal_moved_at on deal (moved_at);
create unique index deal_legacy on deal (legacy_source, legacy_id) where legacy_id is not null;

create table contact_merge (
  id uuid primary key,
  kept_contact_id uuid not null references contact (id) on delete cascade,
  dropped_contact_legacy jsonb not null,
  deals_moved integer not null check (deals_moved >= 0),
  merged_by uuid not null references app_user (id) on delete restrict,
  merged_at timestamptz not null default now()
);
create index contact_merge_kept on contact_merge (kept_contact_id);

create table reminder_log (
  id uuid primary key,
  deal_id uuid not null references deal (id) on delete cascade,
  moved_at timestamptz not null,
  sent_to uuid not null references app_user (id) on delete cascade,
  sent_at timestamptz not null default now(),
  unique (deal_id, moved_at)
);

-- Seed stages (D08)
-- lead(1, open), qualified(2, open), proposal(3, open), won(4, won), lost(5, lost), closed(6, unspecified)
