import { Database, FileText, MapPin, MessageSquare, Search, UserRound } from "lucide-react";
import { useState } from "react";
import { ResumeWorkspace } from "../components/resume/ResumeWorkspace";
import { useAppData } from "../context/AppContext";
import { getResume } from "../services/resumeApi";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { Loader } from "../components/ui/Loader";
import { SessionSkeletons, WorkspaceSkeleton } from "../components/ui/Skeleton";
import { Table, type TableColumn } from "../components/ui/Table";
import type { BulkImportStatus, RecruiterSession, ResumeDetail, ResumeListItem, UUID } from "../types";

export function SessionsPage() {
  const { sessions, activeSessionId, activeSessionResumes, busy, bulkImportStatus, sessionsLoaded, setNotice, updateResumeInState, handleSwitchSession } = useAppData();
  const [candidateSearch, setCandidateSearch] = useState("");
  const [selectedResume, setSelectedResume] = useState<ResumeDetail | null>(null);
  const [workspaceError, setWorkspaceError] = useState("");
  const [switchingSessionId, setSwitchingSessionId] = useState<UUID | null>(null);
  const [openingResumeId, setOpeningResumeId] = useState<UUID | null>(null);
  const [workspaceRestoreStep, setWorkspaceRestoreStep] = useState("");
  const searchTerm = candidateSearch.trim().toLowerCase();
  const displayedSessions = searchTerm
    ? sessions.filter((session) => sessionSearchText(session).includes(searchTerm))
    : sessions;

  const resumeColumns: TableColumn<ResumeListItem>[] = [
    { key: "candidate", header: "Candidate", className: "candidate-column", render: (row) => row.candidate_name || row.original_file_name || "Unnamed" },
    { key: "skills", header: "Skills", className: "skills-column", render: (row) => <SkillChips skills={row.skills || []} /> },
    { key: "decision", header: "Decision", className: "decision-column", render: (row) => <DecisionBadge decision={row.hr_decision} /> },
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
    <>
      <header className="page-header">
        <div>
          <h2>Sessions</h2>
          <p>Manage uploaded resumes and continue reviewing candidates anytime.</p>
        </div>
      </header>

      <section className="split-layout sessions-layout">
        <div className="panel">
          <div className="section-title">
            <h3>Sessions ({sessions.length})</h3>
          </div>
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
          <ImportStatusPanel status={bulkImportStatus} />

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
    </>
  );

  async function openSession(session: RecruiterSession) {
    const sessionId = session.session_id || session.id;
    if (!sessionId) return;
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

  async function openResume(resumeId?: UUID | null) {
    if (!resumeId) return;
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

function ImportStatusPanel({ status }: { status: BulkImportStatus }) {
  const total = status.total || 0;
  const processed = status.processed || 0;
  const progress = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
  const currentFile = status.current_file || "";
  const lastUpdate = formatStatusTime(status.updated_at || status.finished_at || status.started_at);
  const eta = status.running ? estimateImportEta(status) : "";

  if (!status.running) {
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
    <section className="import-status-panel">
      <div className="section-title">
        <div>
          <h3><Database size={17} /> Import Status</h3>
          <span>Bulk resume import is running.</span>
        </div>
        <Badge tone="info">Running</Badge>
      </div>
      <div className="import-progress-grid">
        <div>
          <strong>{total ? `${processed} of ${total}` : "No active import"}</strong>
          <span>{status.failed ? `${status.failed} failed` : "No failures reported"}</span>
        </div>
        <div className="import-current-file">
          <span>{status.running ? "Current file" : "Last update"}</span>
          <strong>{currentFile || status.message || "Preparing next resume..."}</strong>
        </div>
      </div>
      <div className="progress-track">
        <div
          className={`progress-bar ${!total ? "is-indeterminate" : ""}`}
          style={total ? { width: `${progress}%` } : undefined}
        />
      </div>
      <div className="import-runtime-meta">
        <small>{total ? `${progress}% complete` : "Calculating progress..."}</small>
        <small>{eta ? `ETA ${eta}` : "ETA calculating"}</small>
        <small>Updated {lastUpdate}</small>
      </div>
    </section>
  );
}

function formatStatusTime(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return date.toLocaleString();
}

function estimateImportEta(status: BulkImportStatus) {
  const startedAt = status.started_at ? new Date(status.started_at).getTime() : 0;
  const processed = status.processed || 0;
  const total = status.total || 0;
  if (!startedAt || !processed || !total || processed >= total) return "";

  const elapsedMs = Date.now() - startedAt;
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
    <button className={`session-row ${active ? "is-active" : ""}`} disabled={disabled} onClick={onClick}>
      <strong><UserRound size={15} /> {candidateName} {loading && <Loader label="" />}</strong>
      <span>{primaryCity ? <><MapPin size={13} /> {primaryCity}</> : <><FileText size={13} /> {session.document_count || 0} resume{(session.document_count || 0) === 1 ? "" : "s"}</>}</span>
      <span><MessageSquare size={13} /> {session.message_count || 0} chats <DecisionBadge decision={session.hr_decision} compact /></span>
    </button>
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
