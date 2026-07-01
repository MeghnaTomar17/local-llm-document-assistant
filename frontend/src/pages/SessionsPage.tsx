import { FileText, MapPin, MessageSquare, Search, UserRound } from "lucide-react";
import { useState } from "react";
import { ResumeWorkspace } from "../components/resume/ResumeWorkspace";
import { useAppData } from "../context/AppContext";
import { getApiError } from "../services/http";
import { getResume } from "../services/resumeApi";
import { UploadPanel } from "../components/upload/UploadPanel";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { Table, type TableColumn } from "../components/ui/Table";
import type { RecruiterSession, ResumeDetail, ResumeListItem, UUID } from "../types";

export function SessionsPage() {
  const { sessions, activeSessionId, activeSessionResumes, busy, setNotice, updateResumeInState, handleSwitchSession, handleUpload } = useAppData();
  const [candidateSearch, setCandidateSearch] = useState("");
  const [selectedResume, setSelectedResume] = useState<ResumeDetail | null>(null);
  const [workspaceError, setWorkspaceError] = useState("");
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
            {displayedSessions.length ? displayedSessions.map((session) => (
              <SessionButton
                key={session.session_id || session.id}
                session={session}
                active={activeSessionId === (session.session_id || session.id)}
                disabled={busy}
                onClick={() => openSession(session)}
              />
            )) : (
              <EmptyState
                icon={<FileText size={24} />}
                title={searchTerm ? "No matching resumes found." : "No sessions found."}
                description={searchTerm ? "Clear the search to see every candidate." : "Upload resumes to start reviewing candidates."}
              />
            )}
          </div>
        </div>

        <div className="panel session-main-panel">
          <div className="section-title">
            <h3>Active session resumes</h3>
            <Badge tone="info">{activeSessionResumes.length} resumes</Badge>
          </div>
          <UploadPanel disabled={busy} sessionId={null} onUpload={handleUpload} />

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
            {selectedResume ? (
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
    try {
      await handleSwitchSession(sessionId);
      const resumeId = session.resume_id || session.document?.resume_id;
      if (resumeId) {
        setSelectedResume(await getResume(resumeId));
      }
    } catch (err) {
      setWorkspaceError(getApiError(err));
    }
  }

  async function openResume(resumeId?: UUID | null) {
    if (!resumeId) return;
    setWorkspaceError("");
    try {
      setSelectedResume(await getResume(resumeId));
    } catch (err) {
      setWorkspaceError(getApiError(err));
    }
  }
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
  onClick,
}: {
  session: RecruiterSession;
  active: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const candidateName = session.candidate_name || session.title || session.display_name || session.document?.name || "Resume Session";
  const primaryCity = primarySessionCity(session);

  return (
    <button className={`session-row ${active ? "is-active" : ""}`} disabled={disabled} onClick={onClick}>
      <strong><UserRound size={15} /> {candidateName}</strong>
      <span>{primaryCity ? <><MapPin size={13} /> {primaryCity}</> : <><FileText size={13} /> {session.document_count || 0} resume{(session.document_count || 0) === 1 ? "" : "s"}</>}</span>
      <span><MessageSquare size={13} /> {session.message_count || 0} chats <DecisionBadge decision={session.hr_decision} compact /></span>
    </button>
  );
}

function DecisionBadge({ decision, compact = false }: { decision?: string | null; compact?: boolean }) {
  const value = decision || "PENDING";
  if (value === "ACCEPTED") return <Badge tone="success">{compact ? "Accepted" : "Accepted"}</Badge>;
  if (value === "REJECTED") return <Badge tone="danger">{compact ? "Rejected" : "Rejected"}</Badge>;
  return <Badge tone="warning">{compact ? "Pending" : "Pending Review"}</Badge>;
}

function primarySessionCity(session: RecruiterSession) {
  const cities = (session as RecruiterSession & { cities?: string[] | string | null }).cities;
  if (Array.isArray(cities)) return cities[0] || "";
  return cities || "";
}

function SkillChips({ skills }: { skills: string[] }) {
  const [expanded, setExpanded] = useState(false);
  if (!skills.length) return "-";
  const visibleSkills = expanded ? skills : skills.slice(0, 5);
  const remainingCount = skills.length - visibleSkills.length;

  return (
    <div className="skill-chip-list">
      {visibleSkills.map((skill, index) => (
        <span className="skill-chip" key={`${skill}-${index}`}>{skill}</span>
      ))}
      {skills.length > 5 && (
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
