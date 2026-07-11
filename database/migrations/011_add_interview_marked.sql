-- Migration: Add interview_marked column to resumes table
ALTER TABLE resumes ADD COLUMN interview_marked BOOLEAN NOT NULL DEFAULT FALSE;
