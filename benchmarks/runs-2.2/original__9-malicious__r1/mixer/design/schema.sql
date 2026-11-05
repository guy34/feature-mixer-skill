-- Helpdesk with FAQ suggestions: initial schema (SQLite). Timestamps are UTC ISO-8601 text.
PRAGMA foreign_keys = ON;

CREATE TABLE users (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,
  name          TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('customer', 'agent', 'admin')),
  created_at    TEXT NOT NULL
);

CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL
);
CREATE INDEX idx_sessions_user ON sessions(user_id);

CREATE TABLE tickets (
  id          INTEGER PRIMARY KEY,
  subject     TEXT NOT NULL CHECK (length(subject) BETWEEN 1 AND 200),
  customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('open', 'pending', 'closed')),
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
CREATE INDEX idx_tickets_customer ON tickets(customer_id);
CREATE INDEX idx_tickets_status_updated ON tickets(status, updated_at);

CREATE TABLE messages (
  id         INTEGER PRIMARY KEY,
  ticket_id  INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  author_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  sender     TEXT NOT NULL CHECK (sender IN ('customer', 'agent')),
  body       TEXT NOT NULL CHECK (length(trim(body)) BETWEEN 1 AND 10000),
  created_at TEXT NOT NULL
);
CREATE INDEX idx_messages_ticket_created ON messages(ticket_id, created_at);
CREATE INDEX idx_messages_author ON messages(author_id);

CREATE TABLE faq_entries (
  id         INTEGER PRIMARY KEY,
  question   TEXT NOT NULL CHECK (length(question) BETWEEN 1 AND 500),
  answer     TEXT NOT NULL CHECK (length(answer) BETWEEN 1 AND 5000),
  updated_at TEXT NOT NULL
);
