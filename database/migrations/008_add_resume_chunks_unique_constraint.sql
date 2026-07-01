DELETE FROM resume_chunks duplicate_chunk
USING resume_chunks kept_chunk
WHERE duplicate_chunk.resume_id = kept_chunk.resume_id
  AND duplicate_chunk.chunk_index = kept_chunk.chunk_index
  AND duplicate_chunk.id > kept_chunk.id;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_resume_chunks_resume_id_chunk_index'
    ) THEN
        ALTER TABLE resume_chunks
        ADD CONSTRAINT uq_resume_chunks_resume_id_chunk_index
        UNIQUE (resume_id, chunk_index);
    END IF;
END $$;
