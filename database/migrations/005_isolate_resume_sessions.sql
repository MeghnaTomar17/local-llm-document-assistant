-- Ensure each resume has an isolated RecruiterSession for resume chat/RAG.
-- Existing grouped sessions are preserved when they only own one resume; when a
-- session owns multiple resumes, all but one resume receive a new session.

DO $$
DECLARE
    resume_row RECORD;
    sibling_count INTEGER;
    new_session_id UUID;
BEGIN
    FOR resume_row IN
        SELECT *
        FROM resumes
        WHERE session_id IS NOT NULL
        ORDER BY uploaded_at ASC, id ASC
    LOOP
        SELECT COUNT(*)
        INTO sibling_count
        FROM resumes
        WHERE session_id = resume_row.session_id;

        IF sibling_count <= 1 THEN
            UPDATE sessions
            SET title = COALESCE(NULLIF(resume_row.candidate_name, ''), resume_row.original_file_name),
                updated_at = NOW()
            WHERE id = resume_row.session_id;
            CONTINUE;
        END IF;

        INSERT INTO sessions (
            title,
            active,
            created_at,
            updated_at,
            last_accessed,
            chat_history
        )
        VALUES (
            COALESCE(NULLIF(resume_row.candidate_name, ''), resume_row.original_file_name),
            FALSE,
            NOW(),
            NOW(),
            NOW(),
            '[]'::jsonb
        )
        RETURNING id INTO new_session_id;

        UPDATE resumes
        SET session_id = new_session_id,
            updated_at = NOW()
        WHERE id = resume_row.id;
    END LOOP;
END $$;
