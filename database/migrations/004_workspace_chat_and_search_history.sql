ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS chat_history JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS recruiter_search_history (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    results_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,
    execution_time_ms DOUBLE PRECISION,
    model_used TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_recruiter_search_history_session_id
ON recruiter_search_history(session_id);

CREATE INDEX IF NOT EXISTS ix_recruiter_search_history_created_at
ON recruiter_search_history(created_at DESC);
