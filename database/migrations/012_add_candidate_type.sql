-- Migration: Add candidate_type column to resumes table
ALTER TABLE resumes ADD COLUMN candidate_type VARCHAR(20) NOT NULL DEFAULT 'EXTERNAL';
