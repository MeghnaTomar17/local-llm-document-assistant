CREATE TABLE IF NOT EXISTS resume_chunks (
    id UUID PRIMARY KEY,
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    section TEXT,
    title TEXT,
    page_number INTEGER,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_resume_chunks_resume_id_chunk_index UNIQUE (resume_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS ix_resume_chunks_resume_id
ON resume_chunks(resume_id);

CREATE INDEX IF NOT EXISTS ix_resume_chunks_resume_id_chunk_index
ON resume_chunks(resume_id, chunk_index);
