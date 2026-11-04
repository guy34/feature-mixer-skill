-- FileShare unified schema (SQLite). Created from empty by app/fileshare/db.py.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,                       -- uuid4 hex
  username TEXT NOT NULL UNIQUE CHECK (length(username) BETWEEN 3 AND 64),
  password_hash TEXT NOT NULL,               -- pbkdf2_sha256$iterations$salt$hash
  created_at TEXT NOT NULL                   -- ISO-8601 UTC
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at REAL NOT NULL                   -- epoch seconds UTC
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS files (           -- A:File (+ B:File id, name)
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 255),
  size INTEGER NOT NULL CHECK (size >= 0 AND size <= 10485760),
  content_type TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_files_owner_created ON files(owner_id, created_at);
CREATE TABLE IF NOT EXISTS file_content (    -- B:File.data
  file_id TEXT PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
  data BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS share_links (     -- C:ShareLink
  token TEXT PRIMARY KEY,
  file_id TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  expires_at REAL NOT NULL,
  password_hash TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_links_file ON share_links(file_id);
