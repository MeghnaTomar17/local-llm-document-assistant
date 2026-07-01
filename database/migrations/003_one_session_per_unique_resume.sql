CREATE TABLE IF NOT EXISTS duplicate_resume_review (
    id UUID PRIMARY KEY,
    canonical_resume_id UUID NOT NULL,
    resume_hash VARCHAR(64) NOT NULL,
    original_file_name TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

DO $$
DECLARE
    resume_row RECORD;
    canonical_id UUID;
    new_session_id UUID;
BEGIN
    FOR resume_row IN
        SELECT *
        FROM resumes
        ORDER BY uploaded_at ASC, id ASC
    LOOP
        SELECT id
        INTO canonical_id
        FROM resumes
        WHERE resume_hash = resume_row.resume_hash
          AND id <> resume_row.id
          AND uploaded_at <= resume_row.uploaded_at
        ORDER BY uploaded_at ASC, id ASC
        LIMIT 1;

        IF canonical_id IS NOT NULL THEN
            INSERT INTO duplicate_resume_review (
                id,
                canonical_resume_id,
                resume_hash,
                original_file_name,
                reason
            )
            VALUES (
                resume_row.id,
                canonical_id,
                resume_row.resume_hash,
                resume_row.original_file_name,
                'Duplicate resume_hash; review before deleting because metadata, notes, or verification state may differ.'
            )
            ON CONFLICT (id) DO NOTHING;

            CONTINUE;
        END IF;

        IF resume_row.session_id IS NULL THEN
            INSERT INTO sessions (
                title,
                active,
                created_at,
                updated_at,
                last_accessed
            )
            VALUES (
                COALESCE(NULLIF(resume_row.candidate_name, ''), resume_row.original_file_name),
                FALSE,
                NOW(),
                NOW(),
                NOW()
            )
            RETURNING id INTO new_session_id;

            UPDATE resumes
            SET session_id = new_session_id,
                updated_at = NOW()
            WHERE id = resume_row.id;
        ELSE
            UPDATE sessions
            SET title = COALESCE(NULLIF(resume_row.candidate_name, ''), resume_row.original_file_name),
                updated_at = NOW()
            WHERE id = resume_row.session_id;
        END IF;
    END LOOP;
END $$;
