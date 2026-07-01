ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS hr_decision VARCHAR(20) NOT NULL DEFAULT 'PENDING';

ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS decision_at TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_resumes_hr_decision'
    ) THEN
        ALTER TABLE resumes
        ADD CONSTRAINT ck_resumes_hr_decision
        CHECK (hr_decision IN ('PENDING', 'ACCEPTED', 'REJECTED'));
    END IF;
END $$;
