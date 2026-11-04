create table users (
  id serial primary key,
  email text not null unique,
  full_name text not null,
  role text not null check (role in ('requester', 'approver', 'admin'))
);

create table approval_requests (
  id serial primary key,
  title text not null,
  requester_id integer not null references users(id),
  approver_id integer references users(id),
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  decided_at timestamp
);

create table comments (
  id serial primary key,
  request_id integer not null references approval_requests(id) on delete cascade,
  parent_id integer references comments(id) on delete cascade,
  author_id integer not null references users(id),
  body text not null
);

create table email_outbox (
  id serial primary key,
  to_address text not null,
  subject text not null,
  body text not null,
  sent_at timestamp
);
