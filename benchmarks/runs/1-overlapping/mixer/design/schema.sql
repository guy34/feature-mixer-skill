-- Unified Notes schema (SQLite). Plan only: not run.
PRAGMA foreign_keys = ON;

CREATE TABLE notes (
  id          TEXT PRIMARY KEY,                 -- uuid v4 (A: integer re-keyed, B: uuid kept)
  legacy_id   INTEGER UNIQUE,                   -- A's integer id during migration
  title       TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 200),
  body        TEXT NOT NULL DEFAULT '',         -- A.body, B.content
  pinned      INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1)),
  created_at  TEXT NOT NULL,                    -- UTC ISO-8601
  updated_at  TEXT NOT NULL                     -- UTC ISO-8601, refreshed on every edit
);
CREATE INDEX notes_list_order ON notes (pinned DESC, created_at DESC);

CREATE TABLE tags (
  id         TEXT PRIMARY KEY,                  -- uuid v4
  legacy_id  INTEGER UNIQUE,
  name       TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 50)
);
CREATE UNIQUE INDEX tags_name_ci ON tags (lower(name));

CREATE TABLE note_tags (
  note_id  TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  tag_id   TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (note_id, tag_id)
);
CREATE INDEX note_tags_tag ON note_tags (tag_id);
