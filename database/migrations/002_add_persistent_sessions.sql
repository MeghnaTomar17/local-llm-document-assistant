CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'Resume Session',
    active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS session_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'resumes_session_id_fkey'
    ) THEN
        ALTER TABLE resumes
        ADD CONSTRAINT resumes_session_id_fkey
        FOREIGN KEY (session_id)
        REFERENCES sessions(id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_resumes_session_id
ON resumes(session_id);

INSERT INTO sessions (id, title, active, created_at, updated_at, last_accessed)
SELECT gen_random_uuid(), 'Default Session', TRUE, NOW(), NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sessions);

UPDATE resumes
SET session_id = (SELECT id FROM sessions ORDER BY created_at ASC LIMIT 1)
WHERE session_id IS NULL;
