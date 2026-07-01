-- Sync the existing sessions table with database.models.RecruiterSession.
-- This migration is intentionally additive/idempotent and preserves data.

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS title TEXT;

UPDATE sessions
SET title = 'Resume Session'
WHERE title IS NULL OR btrim(title) = '';

ALTER TABLE sessions
ALTER COLUMN title SET DEFAULT 'Resume Session',
ALTER COLUMN title SET NOT NULL;

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS active BOOLEAN;

UPDATE sessions
SET active = FALSE
WHERE active IS NULL;

ALTER TABLE sessions
ALTER COLUMN active SET DEFAULT FALSE,
ALTER COLUMN active SET NOT NULL;

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;

UPDATE sessions
SET created_at = NOW()
WHERE created_at IS NULL;

ALTER TABLE sessions
ALTER COLUMN created_at SET DEFAULT NOW();

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

UPDATE sessions
SET updated_at = COALESCE(created_at, NOW())
WHERE updated_at IS NULL;

ALTER TABLE sessions
ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMPTZ;

UPDATE sessions
SET last_accessed = COALESCE(updated_at, created_at, NOW())
WHERE last_accessed IS NULL;

ALTER TABLE sessions
ALTER COLUMN last_accessed SET DEFAULT NOW();

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS chat_history JSONB;

UPDATE sessions
SET chat_history = '[]'::jsonb
WHERE chat_history IS NULL;

ALTER TABLE sessions
ALTER COLUMN chat_history SET DEFAULT '[]'::jsonb,
ALTER COLUMN chat_history SET NOT NULL;
