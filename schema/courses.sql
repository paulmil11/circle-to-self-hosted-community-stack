-- Optional extension. Apply schema/community.sql first.
-- This schema stores content/state; your server must enforce authorization.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS courses (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  entitlement_key TEXT NOT NULL,
  published INTEGER NOT NULL DEFAULT 0 CHECK (published IN (0, 1))
);

CREATE TABLE IF NOT EXISTS course_modules (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  position INTEGER NOT NULL CHECK (position >= 0),
  UNIQUE (course_id, id),
  UNIQUE (course_id, position)
);

CREATE TABLE IF NOT EXISTS course_lessons (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  module_id TEXT NOT NULL,
  title TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('text', 'video', 'audio', 'exercise')),
  position INTEGER NOT NULL CHECK (position >= 0),
  body_markdown TEXT NOT NULL DEFAULT '',
  media_provider TEXT CHECK (media_provider IN ('mux', 'stream', 'r2')),
  media_asset_key TEXT,
  published INTEGER NOT NULL DEFAULT 0 CHECK (published IN (0, 1)),
  FOREIGN KEY (course_id, module_id) REFERENCES course_modules(course_id, id) ON DELETE CASCADE,
  UNIQUE (module_id, position),
  CHECK ((media_provider IS NULL) = (media_asset_key IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_course_lessons_course ON course_lessons(course_id);

CREATE TABLE IF NOT EXISTS course_progress (
  member_id TEXT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  lesson_id TEXT NOT NULL REFERENCES course_lessons(id) ON DELETE CASCADE,
  position_seconds INTEGER NOT NULL DEFAULT 0 CHECK (position_seconds >= 0),
  completed_at TEXT,
  revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (member_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS course_notes (
  member_id TEXT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  lesson_id TEXT NOT NULL REFERENCES course_lessons(id) ON DELETE CASCADE,
  prompt_key TEXT NOT NULL,
  answer_text TEXT NOT NULL DEFAULT '',
  revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (member_id, lesson_id, prompt_key)
);

CREATE INDEX IF NOT EXISTS idx_course_progress_lesson ON course_progress(lesson_id);
CREATE INDEX IF NOT EXISTS idx_course_notes_lesson ON course_notes(lesson_id);
