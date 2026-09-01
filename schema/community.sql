PRAGMA foreign_keys = ON;

-- Raw import evidence. These tables contain personal data and may not belong in
-- the production database. The D1 export script excludes them by default.
CREATE TABLE IF NOT EXISTS circle_import_batches (
  id TEXT PRIMARY KEY,
  community_key TEXT NOT NULL,
  source_digest TEXT NOT NULL,
  source_path TEXT NOT NULL,
  imported_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (community_key, source_digest)
);

CREATE TABLE IF NOT EXISTS circle_raw_members (
  import_batch_id TEXT NOT NULL REFERENCES circle_import_batches(id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  circle_user_id TEXT,
  email TEXT,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (import_batch_id, row_number)
);

CREATE TABLE IF NOT EXISTS circle_raw_spaces (
  import_batch_id TEXT NOT NULL REFERENCES circle_import_batches(id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  circle_space_id TEXT,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (import_batch_id, row_number)
);

CREATE TABLE IF NOT EXISTS circle_raw_posts (
  import_batch_id TEXT NOT NULL REFERENCES circle_import_batches(id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  circle_post_id TEXT,
  circle_member_id TEXT,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (import_batch_id, row_number)
);

CREATE TABLE IF NOT EXISTS circle_raw_comments (
  import_batch_id TEXT NOT NULL REFERENCES circle_import_batches(id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  circle_comment_id TEXT,
  circle_post_id TEXT,
  circle_member_id TEXT,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (import_batch_id, row_number)
);

CREATE TABLE IF NOT EXISTS circle_raw_events (
  import_batch_id TEXT NOT NULL REFERENCES circle_import_batches(id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  circle_event_id TEXT,
  circle_member_id TEXT,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (import_batch_id, row_number)
);

-- Normalized system of record.
CREATE TABLE IF NOT EXISTS circle_spaces (
  circle_space_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT,
  is_private INTEGER,
  is_hidden_from_non_members INTEGER,
  source TEXT NOT NULL DEFAULT 'spaces_csv',
  imported_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_circle_spaces_name
  ON circle_spaces(name);

CREATE TABLE IF NOT EXISTS members (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  first_name TEXT,
  last_name TEXT,
  display_name TEXT NOT NULL,
  avatar_url TEXT,
  headline TEXT,
  bio TEXT,
  location_text TEXT,
  website_url TEXT,
  social_links_json TEXT NOT NULL DEFAULT '{}',
  lifecycle_status TEXT NOT NULL DEFAULT 'unknown'
    CHECK (lifecycle_status IN ('active', 'cancelled', 'gifted', 'lifetime', 'unknown')),
  onboarding_status TEXT NOT NULL DEFAULT 'imported',
  circle_user_id TEXT,
  circle_profile_url TEXT,
  circle_joined_at TEXT,
  circle_last_active_at TEXT,
  circle_active_30d INTEGER NOT NULL DEFAULT 0,
  circle_activity_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_members_circle_user_id
  ON members(circle_user_id);

CREATE INDEX IF NOT EXISTS idx_members_lifecycle
  ON members(lifecycle_status);

CREATE TABLE IF NOT EXISTS member_import_sources (
  member_id TEXT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  source_user_id TEXT,
  import_batch_id TEXT NOT NULL REFERENCES circle_import_batches(id) ON DELETE CASCADE,
  raw_json TEXT NOT NULL,
  imported_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (member_id, source, import_batch_id)
);

CREATE TABLE IF NOT EXISTS member_tags (
  member_id TEXT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  tag TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'circle',
  imported_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (member_id, tag, source)
);

CREATE TABLE IF NOT EXISTS member_space_access (
  member_id TEXT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  circle_space_id TEXT NOT NULL REFERENCES circle_spaces(circle_space_id) ON DELETE CASCADE,
  source TEXT NOT NULL DEFAULT 'circle',
  imported_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (member_id, circle_space_id, source)
);

-- Member-owned fields stay separate from import-prefill fields. Import scripts
-- never overwrite confirmed values in this table.
CREATE TABLE IF NOT EXISTS member_profiles (
  member_id TEXT PRIMARY KEY REFERENCES members(id) ON DELETE CASCADE,
  preferred_name TEXT,
  headline TEXT,
  bio TEXT,
  location_text TEXT,
  location_lat REAL,
  location_lng REAL,
  timezone TEXT,
  contact_links_json TEXT NOT NULL DEFAULT '{}',
  interests_json TEXT NOT NULL DEFAULT '[]',
  skills_json TEXT NOT NULL DEFAULT '[]',
  matching_preferences_json TEXT NOT NULL DEFAULT '{}',
  privacy_json TEXT NOT NULL DEFAULT '{"directory_visible":false,"location_visible":false}',
  prefill_json TEXT NOT NULL DEFAULT '{}',
  confirmed_at TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS member_email_preferences (
  member_id TEXT PRIMARY KEY REFERENCES members(id) ON DELETE CASCADE,
  digest_enabled INTEGER NOT NULL DEFAULT 0,
  events_enabled INTEGER NOT NULL DEFAULT 0,
  matching_enabled INTEGER NOT NULL DEFAULT 0,
  nearby_members_enabled INTEGER NOT NULL DEFAULT 0,
  pause_all INTEGER NOT NULL DEFAULT 0,
  source TEXT NOT NULL DEFAULT 'migration',
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS member_entitlements (
  id TEXT PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  entitlement_key TEXT NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'provisional'
    CHECK (status IN ('provisional', 'active', 'expired', 'revoked')),
  starts_at TEXT,
  ends_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (member_id, entitlement_key, source)
);

CREATE INDEX IF NOT EXISTS idx_entitlements_member_status
  ON member_entitlements(member_id, status);

CREATE VIEW IF NOT EXISTS v_circle_import_summary AS
SELECT 'import_batches' AS item, count(*) AS count FROM circle_import_batches
UNION ALL SELECT 'raw_members', count(*) FROM circle_raw_members
UNION ALL SELECT 'raw_spaces', count(*) FROM circle_raw_spaces
UNION ALL SELECT 'raw_posts', count(*) FROM circle_raw_posts
UNION ALL SELECT 'raw_comments', count(*) FROM circle_raw_comments
UNION ALL SELECT 'raw_events', count(*) FROM circle_raw_events
UNION ALL SELECT 'members', count(*) FROM members
UNION ALL SELECT 'spaces', count(*) FROM circle_spaces
UNION ALL SELECT 'tags', count(*) FROM member_tags
UNION ALL SELECT 'space_access', count(*) FROM member_space_access
UNION ALL SELECT 'profiles', count(*) FROM member_profiles
UNION ALL SELECT 'entitlements', count(*) FROM member_entitlements;
