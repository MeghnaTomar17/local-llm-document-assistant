-- Recruiter search is independent from resume chat sessions.
-- Keep the FK for older session-scoped history rows, but allow global searches
-- to be stored without requiring a RecruiterSession.

ALTER TABLE recruiter_search_history
ALTER COLUMN session_id DROP NOT NULL;
