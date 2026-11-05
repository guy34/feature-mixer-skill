-- Unified reading app: SQLite schema (first migration). Timestamps are UTC ISO-8601 text.
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE user (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(email) BETWEEN 3 AND 254),
  password_hash TEXT NOT NULL,
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE session (
  id         TEXT PRIMARY KEY,               -- SHA-256 of the cookie token; the token itself is never stored
  user_id    INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  expires_at TEXT NOT NULL
);
CREATE INDEX session_user_id ON session(user_id);
CREATE INDEX session_expires_at ON session(expires_at);

-- merged from A:Book (id, title, author) and B:Book (id, title)
CREATE TABLE book (
  id         INTEGER PRIMARY KEY,
  owner_id   INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  title      TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 300),
  author     TEXT CHECK (author IS NULL OR length(author) <= 300),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX book_owner_title ON book(owner_id, title);

-- from A:Rating; 1-5 as both codebases enforce (Shelfie's documented 1-10 'score' is stale)
CREATE TABLE rating (
  id         INTEGER PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  book_id    INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
  stars      INTEGER NOT NULL CHECK (typeof(stars) = 'integer' AND stars BETWEEN 1 AND 5),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE (user_id, book_id)
);
CREATE INDEX rating_book_id ON rating(book_id);

-- from B:List
CREATE TABLE reading_list (
  id         INTEGER PRIMARY KEY,
  owner_id   INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  name       TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 100),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE (owner_id, name)
);
CREATE INDEX reading_list_owner_id ON reading_list(owner_id);

-- from B:ListBook; a book appears at most once per list
CREATE TABLE reading_list_item (
  list_id  INTEGER NOT NULL REFERENCES reading_list(id) ON DELETE CASCADE,
  book_id  INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
  added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY (list_id, book_id)
);
CREATE INDEX reading_list_item_book_id ON reading_list_item(book_id);
