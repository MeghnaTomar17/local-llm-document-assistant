import type { ResumeUploadProgress } from "../../context/AppContext";

export function ResumeUploadProgressPanel({ progress, global = false }: { progress: ResumeUploadProgress; global?: boolean }) {
  const percentage = progress.total ? Math.round((progress.completed / progress.total) * 100) : 0;
  const title = progress.complete
    ? `${progress.processed} resumes processed`
    : progress.total === 1
      ? "Processing resume"
      : "Processing resumes...";
  const summary = progress.complete
    ? `${progress.processed} processed · ${progress.duplicates} duplicates · ${progress.failed} failed`
    : `Processing: ${progress.currentFile}`;

  return (
    <div className={`session-upload-progress ${global ? "global-resume-upload-progress" : ""}`.trim()} aria-live="polite">
      <div className="session-upload-progress-heading">
        <strong>{title}</strong>
        <span>{progress.completed} / {progress.total}</span>
      </div>
      <div className="progress-track" aria-label={`${percentage}% complete`}>
        <div className={`progress-bar ${progress.complete ? "" : "is-live"}`.trim()} style={{ width: `${percentage}%` }} />
      </div>
      <div className="session-upload-progress-meta">
        <span>{summary}</span>
        <span>{percentage}%</span>
      </div>
    </div>
  );
}
