import { Database, FileText, MapPin, MessageSquare, Search, Target, UploadCloud, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ResumeWorkspace } from "../components/resume/ResumeWorkspace";
import { useAppData } from "../context/AppContext";
import { getResume } from "../services/resumeApi";
import { uploadResumes } from "../services/importApi";
import { getApiError } from "../services/http";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { Loader } from "../components/ui/Loader";
import { SessionSkeletons, WorkspaceSkeleton } from "../components/ui/Skeleton";
import { Table, type TableColumn } from "../components/ui/Table";
import type { BulkImportStatus, RecruiterSession, ResumeDetail, ResumeListItem, UUID } from "../types";

type SessionUploadProgress = {
  total: number;
  completed: number;
  processed: number;
  duplicates: number;
  failed: number;
  currentFile: string;
  complete: boolean;
};

export function SessionsPage() {
  const { sessions, activeSessionId, activeSessionResumes, busy, bulkImportStatus, sessionsLoaded, refresh, setNotice, updateResumeInState, handleSwitchSession } = useAppData();
  const [candidateSearch, setCandidateSearch] = useState("");
  const [selectedResume, setSelectedResume] = useState<ResumeDetail | null>(null);
  const [workspaceError, setWorkspaceError] = useState("");
  const [switchingSessionId, setSwitchingSessionId] = useState<UUID | null>(null);
  const [openingResumeId, setOpeningResumeId] = useState<UUID | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<SessionUploadProgress | null>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const [classificationFilter, setClassificationFilter] = useState<"ALL" | "INTERNAL" | "EXTERNAL">(() => {
    return (localStorage.getItem("sessions_classification_filter") as "ALL" | "INTERNAL" | "EXTERNAL") || "ALL";
  });

  useEffect(() => {
    localStorage.setItem("sessions_classification_filter", classificationFilter);
  }, [classificationFilter]);

  const [workspaceRestoreStep, setWorkspaceRestoreStep] = useState("");
  const searchTerm = candidateSearch.trim().toLowerCase();
  const displayedSessions = sessions.filter((session) => {
    if (searchTerm && !sessionSearchText(session).includes(searchTerm)) return false;
    const type = session.candidate_type || "EXTERNAL";
    if (classificationFilter === "INTERNAL") return type === "INTERNAL";
    if (classificationFilter === "EXTERNAL") return type === "EXTERNAL";
    return true;
  });

  const resumeColumns: TableColumn<ResumeListItem>[] = [
    { key: "candidate", header: "Candidate", className: "candidate-column", render: (row) => row.candidate_name || row.original_file_name || "Unnamed" },
    { key: "skills", header: "Skills", className: "skills-column", render: (row) => <SkillChips skills={row.skills || []} /> },
    { key: "decision", header: "Decision", className: "decision-column", render: (row) => (
      <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
        <DecisionBadge decision={row.hr_decision} />
        {row.interview_marked && <Badge tone="info"><Target size={12} /> Interview</Badge>}
      </div>
    ) },
    { key: "status", header: "Status", className: "status-column", render: (row) => <Badge tone={row.processing_status === "completed" ? "success" : "neutral"}>{row.processing_status || "Stored"}</Badge> },
  ];

  if (!sessionsLoaded) {
    return (
      <main className="page-loading-state">
        <Loader label="Loading candidate sessions..." />
        <SessionSkeletons count={8} />
      </main>
    );
  }

  return (
    <div className="sessions-page">
      <ImportStatusPanel status={bulkImportStatus} onNotify={setNotice} />

      <header className="page-header">
        <div>
          <h2>Sessions</h2>
          <p>Manage uploaded resumes and continue reviewing candidates anytime.</p>
        </div>
      </header>

      <section className="split-layout sessions-layout">
        <div className="panel">
          <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
            <h3>Sessions ({displayedSessions.length})</h3>
            <div className="segmented-control">
              <button
                type="button"
                className={`segment-btn ${classificationFilter === "ALL" ? "active" : ""}`}
                onClick={() => setClassificationFilter("ALL")}
              >
                All
              </button>
              <button
                type="button"
                className={`segment-btn ${classificationFilter === "INTERNAL" ? "active" : ""}`}
                onClick={() => setClassificationFilter("INTERNAL")}
              >
                Internal
              </button>
              <button
                type="button"
                className={`segment-btn ${classificationFilter === "EXTERNAL" ? "active" : ""}`}
                onClick={() => setClassificationFilter("EXTERNAL")}
              >
                External
              </button>
            </div>
          </div>
          <input
            ref={uploadInputRef}
            className="session-upload-input"
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            multiple
            onChange={(event) => handleUpload(event.target.files)}
          />
          {uploadProgress ? (
            <SessionUploadProgressPanel progress={uploadProgress} />
          ) : (
            <button
              type="button"
              className={`session-upload-dropzone ${dragActive ? "is-dragging" : ""}`.trim()}
              disabled={uploading || busy}
              onClick={() => uploadInputRef.current?.click()}
              onDragEnter={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={(event) => {
                event.preventDefault();
                if (event.currentTarget.contains(event.relatedTarget as Node)) return;
                setDragActive(false);
              }}
              onDrop={(event) => {
                event.preventDefault();
                setDragActive(false);
                handleUpload(event.dataTransfer.files);
              }}
            >
              <UploadCloud size={18} />
              <span>Drop resumes here or click to browse</span>
              <small>PDF, DOCX</small>
            </button>
          )}
          <div className="session-search">
            <Search size={17} />
            <input
              value={candidateSearch}
              onChange={(event) => setCandidateSearch(event.target.value)}
              placeholder="Search candidates..."
            />
          </div>
          <div className="session-list">
            {busy && !displayedSessions.length ? <SessionSkeletons /> : displayedSessions.length ? displayedSessions.map((session) => (
              <SessionButton
                key={session.session_id || session.id}
                session={session}
                active={(switchingSessionId || activeSessionId) === (session.session_id || session.id)}
                disabled={busy}
                loading={switchingSessionId === (session.session_id || session.id)}
                onClick={() => openSession(session)}
              />
            )) : (
              <EmptyState
                icon={<FileText size={24} />}
                title={searchTerm ? "No matching resumes found." : "No sessions found."}
                description={searchTerm ? "Clear the search to see every candidate." : "Run bulk_process.py to import resumes, then this list will refresh automatically."}
              />
            )}
          </div>
        </div>

        <div className="panel session-main-panel">
          <div className="section-title">
            <h3>Active session resumes</h3>
            <Badge tone="info">{activeSessionResumes.length} resumes</Badge>
          </div>

          <div className="active-resume-table">
            {activeSessionResumes.length ? (
              <Table
                columns={resumeColumns}
                rows={activeSessionResumes}
                getRowKey={(row, index) => row.id || String(index)}
                onRowClick={(row) => openResume(row.id)}
              />
            ) : (
              <EmptyState title="No resumes in this session." />
            )}
          </div>

          <div className="embedded-workspace">
            {workspaceError && <div className="error-banner">{workspaceError}</div>}
            {openingResumeId ? (
              <WorkspaceRestoreState step={workspaceRestoreStep} />
            ) : selectedResume ? (
              <ResumeWorkspace
                resume={selectedResume}
                onNotify={setNotice}
                onResumeSaved={async (updated) => {
                  setSelectedResume(updated);
                  updateResumeInState(updated);
                }}
              />
            ) : (
              <EmptyState title="Select a resume to open its workspace." />
            )}
          </div>
        </div>
      </section>
    </div>
  );

  async function openSession(session: RecruiterSession) {
    const sessionId = session.session_id || session.id;
    if (!sessionId) return;
    setNotice("");
    setWorkspaceError("");
    const resumeId = session.resume_id || session.document?.resume_id;
    if (resumeId) setOpeningResumeId(resumeId);
    setWorkspaceRestoreStep("Loading candidate metadata...");
    try {
      setSwitchingSessionId(sessionId);
      setWorkspaceRestoreStep("Restoring stored chunks and chat history...");
      await handleSwitchSession(sessionId);
      if (resumeId) {
        setWorkspaceRestoreStep("Opening individual candidate workspace...");
        setSelectedResume(await getResume(resumeId));
      }
    } catch (err) {
      setWorkspaceError("Unable to load candidate. Please try again.");
    } finally {
      setSwitchingSessionId(null);
      setOpeningResumeId(null);
      setWorkspaceRestoreStep("");
    }
  }

  async function handleUpload(fileList: FileList | null) {
    const files = Array.from(fileList || []);
    if (!files.length || uploading) return;
    if (files.some((file) => !isSupportedResume(file))) {
      setNotice("Only PDF and DOCX resumes are supported.");
      if (uploadInputRef.current) uploadInputRef.current.value = "";
      return;
    }

    setUploading(true);
    setUploadProgress({
      total: files.length,
      completed: 0,
      processed: 0,
      duplicates: 0,
      failed: 0,
      currentFile: files[0].name,
      complete: false,
    });

    let processed = 0;
    let duplicates = 0;
    let failed = 0;
    try {
      for (const [index, file] of files.entries()) {
        setUploadProgress({
          total: files.length,
          completed: index,
          processed,
          duplicates,
          failed,
          currentFile: file.name,
          complete: false,
        });

        try {
          const response = await uploadResumes([file]);
          if (response.uploaded_documents?.length) {
            processed += 1;
          } else if (response.errors?.some((error) => error.duplicate)) {
            duplicates += 1;
          } else {
            failed += 1;
          }
        } catch {
          failed += 1;
        }

        setUploadProgress({
          total: files.length,
          completed: index + 1,
          processed,
          duplicates,
          failed,
          currentFile: file.name,
          complete: index + 1 === files.length,
        });
      }

      await refresh();
      if (processed === 0 && duplicates === 0 && failed > 0) {
        setNotice("Upload failed: No resumes could be processed.");
      } else if (files.length === 1 && duplicates === 1) {
        setNotice("Resume already exists. Duplicate upload skipped.");
      } else {
        setNotice(`${processed} processed · ${duplicates} duplicates skipped · ${failed} failed`);
      }
    } catch (err) {
      setNotice(`Upload failed: ${getApiError(err)}`);
    } finally {
      if (uploadInputRef.current) uploadInputRef.current.value = "";
      await new Promise<void>((resolve) => window.setTimeout(resolve, 1400));
      setUploadProgress(null);
      setUploading(false);
    }
  }

  async function openResume(resumeId?: UUID | null) {
    if (!resumeId) return;
    setNotice("");
    setWorkspaceError("");
    setOpeningResumeId(resumeId);
    setWorkspaceRestoreStep("Loading candidate metadata...");
    try {
      setWorkspaceRestoreStep("Restoring stored chunks and chat history...");
      setSelectedResume(await getResume(resumeId));
    } catch (err) {
      setWorkspaceError("Unable to load candidate. Please try again.");
    } finally {
      setOpeningResumeId(null);
      setWorkspaceRestoreStep("");
    }
  }
}

function isSupportedResume(file: File): boolean {
  return [".pdf", ".docx"].some((extension) => file.name.toLowerCase().endsWith(extension));
}

function SessionUploadProgressPanel({ progress }: { progress: SessionUploadProgress }) {
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
    <div className="session-upload-progress" aria-live="polite">
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

function ImportStatusPanel({ status, onNotify }: { status: BulkImportStatus; onNotify: (msg: string) => void }) {
  const [now, setNow] = useState(Date.now());
  const [showDuplicatesList, setShowDuplicatesList] = useState(false);

  const total = status.total || 0;
  const processed = status.processed || 0;
  const failed = status.failed || 0;
  const duplicates = status.duplicates || 0;
  const infrastructureFailed = status.infrastructure_failed || 0;
  const inferredUnprocessed = total > processed ? total - processed : 0;
  const unprocessed = status.unprocessed ?? inferredUnprocessed;
  const pendingRetry = status.pending_retry ?? Math.max(0, infrastructureFailed + unprocessed);
  const successful = Math.max(0, processed - failed - duplicates - infrastructureFailed);
  const progress = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
  const currentFile = status.current_file || "";
  const lastUpdate = formatStatusTime(status.updated_at || status.finished_at || status.started_at);
  const lifecycleState = getBulkImportState(status);
  const isRunning = lifecycleState === "RUNNING";
  const isInterrupted = lifecycleState === "INTERRUPTED";
  const eta = isRunning ? estimateImportEta(status, now) : "";

  const getAverageProcessingTime = () => {
    if (!status.started_at || processed <= 0) return null;
    const start = new Date(status.started_at).getTime();
    const end = status.finished_at 
      ? new Date(status.finished_at).getTime() 
      : status.updated_at 
        ? new Date(status.updated_at).getTime() 
        : now;
    const diffSeconds = (end - start) / 1000;
    if (diffSeconds <= 0) return null;
    return diffSeconds / processed;
  };
  const avgTime = getAverageProcessingTime();

  const wasRunningRef = useRef(isRunning);

  useEffect(() => {
    if (!isRunning) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [isRunning, status.updated_at]);

  useEffect(() => {
    if (wasRunningRef.current && !isRunning) {
      if (status.duplicate_warnings && status.duplicate_warnings.length > 0) {
        onNotify(`Bulk import ended. ${status.duplicate_warnings.length} resume(s) skipped as duplicates.`);
      }
    }
    wasRunningRef.current = isRunning;
  }, [isRunning, status.duplicate_warnings, onNotify]);

  const showSummary = lifecycleState === "COMPLETED" && status.finished_at && status.total > 0;

  if (showSummary) {
    return (
      <section className="import-status-panel import-status-summary">
        <div className="section-title">
          <div>
            <h3><Database size={17} /> Bulk Import Completed</h3>
            <span>The bulk import process has finished successfully.</span>
          </div>
          <Badge tone="success">Completed</Badge>
        </div>
        
        <div className="import-summary-box">
          <div className="import-summary-grid">
            <div className="summary-item total">
              <span>Total Resumes</span>
              <strong>{total}</strong>
            </div>
            <div className="summary-item success">
              <span>Imported Successfully</span>
              <strong>{successful}</strong>
            </div>
            <div className="summary-item duplicate">
              <span>Duplicates Skipped</span>
              <strong>{duplicates}</strong>
            </div>
            <div className="summary-item failed">
              <span>Document Failed</span>
              <strong>{failed}</strong>
            </div>
            <div className="summary-item warning">
              <span>Infrastructure Failed</span>
              <strong>{infrastructureFailed}</strong>
            </div>
            <div className="summary-item warning">
              <span>Pending Retry</span>
              <strong>{pendingRetry}</strong>
            </div>
            <div className="summary-item total">
              <span>Unprocessed</span>
              <strong>{unprocessed}</strong>
            </div>
            <div className="summary-item info">
              <span>Avg Time / Resume</span>
              <strong>{avgTime !== null ? `${avgTime.toFixed(1)}s` : "-"}</strong>
            </div>
          </div>
        </div>

        {status.duplicate_warnings && status.duplicate_warnings.length > 0 && (
          <div className="duplicate-warnings-section">
            <button 
              type="button" 
              className="toggle-duplicates-btn"
              onClick={() => setShowDuplicatesList(!showDuplicatesList)}
            >
              {showDuplicatesList ? "Hide" : "Show"} Skipped Duplicates ({status.duplicate_warnings.length})
            </button>
            {showDuplicatesList && (
              <ul className="duplicate-warnings-list">
                {status.duplicate_warnings.map((w, idx) => (
                  <li key={idx} className="duplicate-warning-item">
                    <strong>{w.file_name}</strong> – {w.candidate_name} ({w.reason})
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        
        <div className="import-idle-meta">
          <span>Completed At</span>
          <strong>{formatStatusTime(status.finished_at)}</strong>
        </div>
      </section>
    );
  }

  if (isInterrupted) {
    const interruptedTime = formatStatusTime(status.interrupted_at || status.updated_at);
    const progressLabel = total ? `${processed} of ${total} attempted before interruption` : `${processed} attempted before interruption`;
    return (
      <section className="import-status-panel import-status-interrupted">
        <div className="section-title">
          <div>
            <h3><Database size={17} /> Import Status</h3>
            <span>Bulk import was interrupted.</span>
          </div>
          <Badge tone="danger">Interrupted</Badge>
        </div>
        <div className="import-metric-grid">
          <div className="import-metric">
            <span>Attempted</span>
            <strong>{processed}</strong>
          </div>
          <div className="import-metric success">
            <span>Imported</span>
            <strong>{successful}</strong>
          </div>
          <div className="import-metric">
            <span>Duplicates</span>
            <strong>{duplicates}</strong>
          </div>
          <div className="import-metric danger">
            <span>Document failed</span>
            <strong>{failed}</strong>
          </div>
          <div className="import-metric warning">
            <span>Infrastructure failed</span>
            <strong>{infrastructureFailed}</strong>
          </div>
          <div className="import-metric warning">
            <span>Pending retry</span>
            <strong>{pendingRetry}</strong>
          </div>
          <div className="import-metric info">
            <span>Avg Time / Resume</span>
            <strong>{avgTime !== null ? `${avgTime.toFixed(1)}s` : "-"}</strong>
          </div>
        </div>
        <div className="import-progress-grid import-progress-grid-compact">
          <div className="import-current-file">
            <span>Last processed file</span>
            <strong title={status.last_completed_file || currentFile || "None"}>
              {status.last_completed_file || currentFile || "None"}
            </strong>
          </div>
          <div>
            <span>Time interrupted</span>
            <strong>{interruptedTime}</strong>
          </div>
        </div>
        <div className="progress-track">
          <div className="progress-bar is-interrupted" style={{ width: `${progress}%` }} />
        </div>
        <div className="import-runtime-meta">
          <small>{progress}% complete</small>
          <small>{progressLabel}</small>
          {unprocessed > 0 && <small>{unprocessed} unprocessed</small>}
        </div>

        {status.duplicate_warnings && status.duplicate_warnings.length > 0 && (
          <div className="duplicate-warnings-section">
            <button 
              type="button" 
              className="toggle-duplicates-btn"
              onClick={() => setShowDuplicatesList(!showDuplicatesList)}
            >
              {showDuplicatesList ? "Hide" : "Show"} Skipped Duplicates ({status.duplicate_warnings.length})
            </button>
            {showDuplicatesList && (
              <ul className="duplicate-warnings-list">
                {status.duplicate_warnings.map((w, idx) => (
                  <li key={idx} className="duplicate-warning-item">
                    <strong>{w.file_name}</strong> – {w.candidate_name} ({w.reason})
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>
    );
  }

  if (!isRunning) {
    return (
      <section className="import-status-panel import-status-idle">
        <div className="section-title">
          <div>
            <h3><Database size={17} /> Import Status</h3>
            <span>No bulk import is currently running.</span>
          </div>
          <Badge tone="success">System Ready</Badge>
        </div>
        <div className="import-idle-meta">
          <span>Last update</span>
          <strong>{lastUpdate}</strong>
        </div>
      </section>
    );
  }

  return (
    <section className="import-status-panel import-status-running">
      <div className="section-title">
        <div>
          <h3><Database size={17} /> Import Status</h3>
          <span>Bulk resume import is running.</span>
        </div>
        <Badge tone="info">Running</Badge>
      </div>
      <div className="import-progress-grid">
        <div>
          <span>Processed</span>
          <strong>{total ? `${processed} of ${total}` : "0"}</strong>
        </div>
        <div>
          <span>Failed</span>
          <strong>{failed} failed</strong>
        </div>
        <div>
          <span>Avg Time / Resume</span>
          <strong>{avgTime !== null ? `${avgTime.toFixed(1)}s` : "-"}</strong>
        </div>
        {infrastructureFailed > 0 && (
          <div>
            <span>Infrastructure</span>
            <strong>{infrastructureFailed} retrying</strong>
          </div>
        )}
        <div className="import-current-file">
          <span>Current file</span>
          <strong title={currentFile || "Preparing next resume..."}>{currentFile || "Preparing next resume..."}</strong>
        </div>
      </div>
      <div className="progress-track">
        <div
          className={`progress-bar is-live ${!total ? "is-indeterminate" : ""}`}
          style={total ? { width: `${progress}%` } : undefined}
        />
      </div>
      <div className="import-runtime-meta">
        <small>{total ? `${progress}% complete` : "Calculating..."}</small>
        <small>{eta ? `ETA ${eta}` : ""}</small>
      </div>

      {status.duplicate_warnings && status.duplicate_warnings.length > 0 && (
        <div className="duplicate-warnings-section">
          <button 
            type="button" 
            className="toggle-duplicates-btn"
            onClick={() => setShowDuplicatesList(!showDuplicatesList)}
          >
            {showDuplicatesList ? "Hide" : "Show"} Skipped Duplicates ({status.duplicate_warnings.length})
          </button>
          {showDuplicatesList && (
            <ul className="duplicate-warnings-list">
              {status.duplicate_warnings.map((w, idx) => (
                <li key={idx} className="duplicate-warning-item">
                  <strong>{w.file_name}</strong> – {w.candidate_name} ({w.reason})
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function getBulkImportState(status: BulkImportStatus) {
  if (status.state) return status.state;
  if (status.interrupted) return "INTERRUPTED";
  if (status.running) return "RUNNING";
  if (status.finished_at) return "COMPLETED";
  return "IDLE";
}

function formatStatusTime(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return date.toLocaleString();
}

function estimateImportEta(status: BulkImportStatus, now = Date.now()) {
  const startedAt = status.started_at ? new Date(status.started_at).getTime() : 0;
  const processed = status.processed || 0;
  const total = status.total || 0;
  if (!startedAt || !processed || !total || processed >= total) return "";

  const elapsedMs = now - startedAt;
  const averageMs = elapsedMs / processed;
  const remainingMs = Math.max(0, Math.round((total - processed) * averageMs));
  const minutes = Math.floor(remainingMs / 60000);
  const seconds = Math.round((remainingMs % 60000) / 1000);
  if (minutes <= 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

function WorkspaceRestoreState({ step }: { step: string }) {
  return (
    <div className="workspace-restore-state">
      <Loader label={step || "Opening individual candidate workspace..."} />
      <div className="restore-steps">
        <span>Loading metadata</span>
        <span>Restoring stored chunks</span>
        <span>Loading chat history</span>
      </div>
      <WorkspaceSkeleton />
    </div>
  );
}

function sessionSearchText(session: RecruiterSession) {
  return [
    session.candidate_name,
    session.title,
    session.display_name,
    session.original_file_name,
    session.document?.name,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function SessionButton({
  session,
  active,
  disabled,
  loading,
  onClick,
}: {
  session: RecruiterSession;
  active: boolean;
  disabled: boolean;
  loading?: boolean;
  onClick: () => void;
}) {
  const candidateName = session.candidate_name || session.title || session.display_name || session.document?.name || "Resume Session";
  const primaryCity = primarySessionCity(session);

  return (
    <div
      role="button"
      tabIndex={0}
      className={`session-row ${active ? "is-active" : ""}`}
      style={{ cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.7 : 1 }}
      onClick={disabled ? undefined : onClick}
      onKeyDown={(e) => {
        if (!disabled && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <strong><UserRound size={15} /> {candidateName} {loading && <Loader label="" />}</strong>
      <span>{primaryCity ? <><MapPin size={13} /> {primaryCity}</> : <><FileText size={13} /> {session.document_count || 0} resume{(session.document_count || 0) === 1 ? "" : "s"}</>}</span>
      <span style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
        <MessageSquare size={13} /> {session.message_count || 0} chats
        <DecisionBadge decision={session.hr_decision} compact />
        {session.interview_marked && (
          <Badge tone="success">
            <Target size={11} /> Interview
          </Badge>
        )}
        <Badge tone={session.candidate_type === "INTERNAL" ? "success" : "info"}>
          {session.candidate_type === "INTERNAL" ? "Internal" : "External"}
        </Badge>
      </span>
    </div>
  );
}

function DecisionBadge({ decision, compact = false }: { decision?: string | null; compact?: boolean }) {
  const value = decision || "PENDING";
  if (value === "ACCEPTED") return <Badge tone="success">{compact ? "Accepted" : "Accepted"}</Badge>;
  if (value === "REJECTED") return <Badge tone="danger">{compact ? "Rejected" : "Rejected"}</Badge>;
  if (value === "ON_HOLD") return <Badge tone="info">{compact ? "Hold" : "On Hold"}</Badge>;
  return <Badge tone="warning">Pending</Badge>;
}

function primarySessionCity(session: RecruiterSession) {
  const cities = (session as RecruiterSession & { cities?: string[] | string | null }).cities;
  if (Array.isArray(cities)) return cities[0] || "";
  return cities || "";
}

function SkillChips({ skills }: { skills: string[] }) {
  const [expanded, setExpanded] = useState(false);
  if (!skills.length) return "-";
  const visibleSkills = expanded ? skills : skills.slice(0, 3);
  const remainingCount = skills.length - visibleSkills.length;

  return (
    <div className={`skill-chip-list active-skill-chip-list ${expanded ? "is-expanded" : ""}`.trim()}>
      {visibleSkills.map((skill, index) => (
        <span className="skill-chip" key={`${skill}-${index}`}>{skill}</span>
      ))}
      {skills.length > 3 && (
        <button
          className="skill-chip skill-chip-more"
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            setExpanded((current) => !current);
          }}
        >
          {expanded ? "Show less" : `+${remainingCount} more`}
        </button>
      )}
    </div>
  );
}
