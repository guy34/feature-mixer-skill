-- Helpdesk with FAQ suggestions: initial schema (SQLite). PRAGMA foreign_keys = ON at every connection.
CREATE TABLE agent (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,
  name          TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  created_at    TEXT NOT NULL            -- UTC ISO 8601
);

CREATE TABLE session (
  token_hash TEXT PRIMARY KEY,           -- SHA-256 of the cookie token
  agent_id   INTEGER NOT NULL REFERENCES agent(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL
);
CREATE INDEX session_agent_idx ON session(agent_id);

CREATE TABLE ticket (
  id          INTEGER PRIMARY KEY,
  subject     TEXT NOT NULL CHECK (length(trim(subject)) BETWEEN 1 AND 200),
  description TEXT NOT NULL DEFAULT '' CHECK (length(description) <= 10000),
  status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'pending', 'closed')),
  created_by  INTEGER NOT NULL REFERENCES agent(id) ON DELETE RESTRICT,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
CREATE INDEX ticket_status_idx ON ticket(status, created_at);
CREATE INDEX ticket_created_by_idx ON ticket(created_by);

CREATE TABLE message (
  id         INTEGER PRIMARY KEY,
  ticket_id  INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  author_id  INTEGER NOT NULL REFERENCES agent(id) ON DELETE RESTRICT,
  body       TEXT NOT NULL CHECK (length(trim(body)) BETWEEN 1 AND 10000),
  created_at TEXT NOT NULL
);
CREATE INDEX message_ticket_idx ON message(ticket_id, created_at);
CREATE INDEX message_author_idx ON message(author_id);

CREATE TABLE faq (
  id       INTEGER PRIMARY KEY,
  question TEXT NOT NULL,
  answer   TEXT NOT NULL
);

-- Seed: B's one entry (the user's own content).
INSERT INTO faq (question, answer) VALUES
  ('How do I reset my password?', 'Use the reset link on the sign-in page.');
