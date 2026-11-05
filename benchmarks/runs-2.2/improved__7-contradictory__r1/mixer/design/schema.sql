-- Unified schema (SQLite). Run on every connection: PRAGMA foreign_keys = ON;
-- Planned only: nothing has been created or migrated (plan mode).

CREATE TABLE user (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,              -- lower-cased
  password_hash TEXT NOT NULL,                     -- scrypt
  created_at    TEXT NOT NULL                      -- UTC ISO 8601
);

CREATE TABLE session (
  token_hash TEXT PRIMARY KEY,                     -- sha256 of the cookie token
  user_id    INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL
);
CREATE INDEX session_user ON session(user_id);

-- Book: merged from A:Book (id, title, author) and B:Book (id, title)
CREATE TABLE book (
  id         INTEGER PRIMARY KEY,
  owner_id   INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  title      TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 500),
  author     TEXT CHECK (author IS NULL OR length(author) <= 300),
  created_at TEXT NOT NULL
);
CREATE INDEX book_owner ON book(owner_id, title);

-- Rating: from A:Rating; one per person per book (was appended in A and B)
CREATE TABLE rating (
  owner_id   INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  book_id    INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
  stars      INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
  updated_at TEXT NOT NULL,
  PRIMARY KEY (owner_id, book_id)
);
CREATE INDEX rating_book ON rating(book_id);

-- ReadingList: from B:ReadingList (table 'lists')
CREATE TABLE reading_list (
  id         INTEGER PRIMARY KEY,
  owner_id   INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  name       TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 200),
  created_at TEXT NOT NULL
);
CREATE INDEX reading_list_owner ON reading_list(owner_id);

-- ListBook: from B:ListBook (table 'list_books'); duplicates now prevented
CREATE TABLE list_book (
  list_id  INTEGER NOT NULL REFERENCES reading_list(id) ON DELETE CASCADE,
  book_id  INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
  added_at TEXT NOT NULL,
  PRIMARY KEY (list_id, book_id)
);
CREATE INDEX list_book_book ON list_book(book_id);
-- Same-owner rule (list and book belong to the same person) is enforced in the lists module.
