ALTER TABLE recruiter_search_history
ADD COLUMN IF NOT EXISTS no_searchable_criteria BOOLEAN NOT NULL DEFAULT FALSE;
