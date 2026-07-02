ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS hr_notes TEXT;

ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS technical_notes TEXT;

ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS final_notes TEXT;

UPDATE resumes
SET hr_notes = notes
WHERE notes IS NOT NULL
  AND btrim(notes) <> ''
  AND (hr_notes IS NULL OR btrim(hr_notes) = '');

UPDATE resumes
SET hr_decision = 'PENDING'
WHERE hr_decision IS NULL
   OR hr_decision NOT IN ('PENDING', 'ON_HOLD', 'ACCEPTED', 'REJECTED');

ALTER TABLE resumes
ALTER COLUMN hr_decision SET DEFAULT 'PENDING';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_resumes_hr_decision'
    ) THEN
        ALTER TABLE resumes
        DROP CONSTRAINT ck_resumes_hr_decision;
    END IF;
END $$;

ALTER TABLE resumes
ADD CONSTRAINT ck_resumes_hr_decision
CHECK (hr_decision IN ('PENDING', 'ON_HOLD', 'ACCEPTED', 'REJECTED'));
