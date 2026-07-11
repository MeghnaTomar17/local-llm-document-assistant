import { AlertTriangle, CheckCircle2, FileClock, FileText, Globe, Sparkles, Target, UserCheck, Users } from "lucide-react";
import { useAppData } from "../context/AppContext";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { Table, type TableColumn } from "../components/ui/Table";
import type { ResumeListItem } from "../types";

export function DashboardPage() {
  const { resumes, sessions } = useAppData();
  const freshers = resumes.filter((resume) => resume.fresher === true).length;
  const experienced = resumes.filter((resume) => resume.fresher === false).length;
  const verified = resumes.filter((resume) => resume.is_verified === true).length;
  const needsReview = resumes.filter((resume) => !resume.is_verified).length;
  const onHold = resumes.filter((resume) => resume.hr_decision === "ON_HOLD").length;
  const accepted = resumes.filter((resume) => resume.hr_decision === "ACCEPTED").length;
  const rejected = resumes.filter((resume) => resume.hr_decision === "REJECTED").length;
  const pending = resumes.filter((resume) => !resume.hr_decision || resume.hr_decision === "PENDING").length;
  const interviewMarkedCount = resumes.filter((resume) => resume.interview_marked === true).length;
  const internalCount = resumes.filter((resume) => resume.candidate_type === "INTERNAL").length;
  const externalCount = resumes.filter((resume) => resume.candidate_type === "EXTERNAL" || !resume.candidate_type).length;
  const pendingCandidates = [...resumes]
    .filter((resume) => !resume.hr_decision || resume.hr_decision === "PENDING")
    .sort((a, b) => new Date(b.uploaded_at || 0).getTime() - new Date(a.uploaded_at || 0).getTime());
  const recent = [...resumes]
    .sort((a, b) => new Date(b.uploaded_at || 0).getTime() - new Date(a.uploaded_at || 0).getTime())
    .slice(0, 8);

  const columns: TableColumn<ResumeListItem>[] = [
    { key: "name", header: "Candidate", render: (row) => row.candidate_name || row.original_file_name || "Unnamed" },
    { key: "email", header: "Email", render: (row) => row.email || "-" },
    { key: "type", header: "Type", render: (row) => <Badge tone={row.fresher ? "info" : "success"}>{row.fresher ? "Fresher" : "Experienced"}</Badge> },
    { key: "verified", header: "Verified", render: (row) => <Badge tone={row.is_verified ? "success" : "warning"}>{row.is_verified ? "Yes" : "Review"}</Badge> },
    { key: "decision", header: "Decision", render: (row) => <DecisionBadge decision={row.hr_decision} /> },
    { key: "uploaded", header: "Uploaded", render: (row) => formatDate(row.uploaded_at) },
  ];

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p>Get a quick overview of your candidate database and hiring progress.</p>
        </div>
      </header>

      <section className="metrics-grid">
        <Metric icon={<FileText size={19} />} label="Total resumes" value={resumes.length} />
        <Metric icon={<Sparkles size={19} />} label="Freshers" value={freshers} />
        <Metric icon={<Users size={19} />} label="Experienced" value={experienced} />
        <Metric icon={<UserCheck size={19} />} label="Verified" value={verified} />
        <Metric icon={<AlertTriangle size={19} />} label="Needs review" value={needsReview} />
        <Metric icon={<FileClock size={19} />} label="On hold" value={onHold} />
        <Metric icon={<CheckCircle2 size={19} />} label="Accepted" value={accepted} />
        <Metric icon={<AlertTriangle size={19} />} label="Rejected" value={rejected} />
        <Metric icon={<FileClock size={19} />} label="Pending candidates" value={pending} />
        <Metric icon={<Target size={19} />} label="Marked for Interview" value={interviewMarkedCount} />
        <Metric icon={<Users size={19} />} label="Internal Candidates" value={internalCount} />
        <Metric icon={<Globe size={19} />} label="External Candidates" value={externalCount} />
      </section>

      <section className="panel">
        <div className="section-title">
          <h3>Pending Candidates</h3>
          <span>Candidates waiting for a hiring decision.</span>
        </div>
        {pendingCandidates.length ? (
          <Table columns={columns} rows={pendingCandidates} getRowKey={(row, index) => row.id || String(index)} />
        ) : (
          <EmptyState icon={<FileText size={26} />} title="No pending candidates." description="Candidates with saved hiring decisions will move out of this list." />
        )}
      </section>
    </>
  );
}

function DecisionBadge({ decision }: { decision?: string | null }) {
  if (decision === "ACCEPTED") return <Badge tone="success">Accepted</Badge>;
  if (decision === "REJECTED") return <Badge tone="danger">Rejected</Badge>;
  if (decision === "ON_HOLD") return <Badge tone="info">On Hold</Badge>;
  return <Badge tone="warning">Pending</Badge>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <article className="metric-tile">
      {icon}
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
    </article>
  );
}

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleDateString() : "-";
}
