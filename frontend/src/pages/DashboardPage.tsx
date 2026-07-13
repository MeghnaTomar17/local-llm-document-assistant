import { AlertTriangle, CheckCircle2, FileClock, FileText, Globe, Search, Sparkles, Target, UserCheck, Users } from "lucide-react";
import { useMemo, useState } from "react";
import { useAppData } from "../context/AppContext";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { Table, type TableColumn } from "../components/ui/Table";
import type { ResumeListItem } from "../types";

type DashboardFilter =
  | "ALL"
  | "PENDING"
  | "ACCEPTED"
  | "REJECTED"
  | "INTERVIEW"
  | "INTERNAL"
  | "EXTERNAL"
  | "FRESHERS"
  | "EXPERIENCED"
  | "VERIFIED"
  | "NEEDS_REVIEW"
  | "ON_HOLD";

export function DashboardPage() {
  const { resumes } = useAppData();
  const [activeDashboardFilter, setActiveDashboardFilter] = useState<DashboardFilter>("PENDING");
  const [searchTerm, setSearchTerm] = useState("");

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

  const getPercentage = (count: number) => {
    if (!resumes.length) return "0%";
    return `${Math.round((count / resumes.length) * 100)}%`;
  };

  const filteredCandidates = useMemo(() => {
    let list = [...resumes];

    // 1. Filter by category
    switch (activeDashboardFilter) {
      case "PENDING":
        list = list.filter((r) => !r.hr_decision || r.hr_decision === "PENDING");
        break;
      case "ACCEPTED":
        list = list.filter((r) => r.hr_decision === "ACCEPTED");
        break;
      case "REJECTED":
        list = list.filter((r) => r.hr_decision === "REJECTED");
        break;
      case "INTERVIEW":
        list = list.filter((r) => r.interview_marked === true);
        break;
      case "INTERNAL":
        list = list.filter((r) => r.candidate_type === "INTERNAL");
        break;
      case "EXTERNAL":
        list = list.filter((r) => r.candidate_type === "EXTERNAL" || !r.candidate_type);
        break;
      case "FRESHERS":
        list = list.filter((r) => r.fresher === true);
        break;
      case "EXPERIENCED":
        list = list.filter((r) => r.fresher === false);
        break;
      case "VERIFIED":
        list = list.filter((r) => r.is_verified === true);
        break;
      case "NEEDS_REVIEW":
        list = list.filter((r) => !r.is_verified);
        break;
      case "ON_HOLD":
        list = list.filter((r) => r.hr_decision === "ON_HOLD");
        break;
      case "ALL":
      default:
        break;
    }

    // 2. Filter by search term within current category
    const query = searchTerm.trim().toLowerCase();
    if (query) {
      list = list.filter((r) => {
        const name = (r.candidate_name || r.original_file_name || "").toLowerCase();
        const email = (r.email || "").toLowerCase();
        const phone = (r.phone_number || "").toLowerCase();
        const skills = Array.isArray(r.skills)
          ? r.skills.join(" ").toLowerCase()
          : typeof r.skills === "string"
          ? r.skills.toLowerCase()
          : "";
        return name.includes(query) || email.includes(query) || phone.includes(query) || skills.includes(query);
      });
    }

    // 3. Sort by upload date desc by default
    return list.sort((a, b) => new Date(b.uploaded_at || 0).getTime() - new Date(a.uploaded_at || 0).getTime());
  }, [resumes, activeDashboardFilter, searchTerm]);

  const tableTitle = useMemo(() => {
    switch (activeDashboardFilter) {
      case "ALL":
        return "All Candidates";
      case "PENDING":
        return "Pending Candidates";
      case "ACCEPTED":
        return "Accepted Candidates";
      case "REJECTED":
        return "Rejected Candidates";
      case "INTERVIEW":
        return "Interview Candidates";
      case "INTERNAL":
        return "Internal Candidates";
      case "EXTERNAL":
        return "External Candidates";
      case "FRESHERS":
        return "Fresher Candidates";
      case "EXPERIENCED":
        return "Experienced Candidates";
      case "VERIFIED":
        return "Verified Candidates";
      case "NEEDS_REVIEW":
        return "Candidates Needing Review";
      case "ON_HOLD":
        return "Candidates On Hold";
      default:
        return "Candidates";
    }
  }, [activeDashboardFilter]);

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
        <Metric
          icon={<FileText size={19} />}
          label="Total resumes"
          value={resumes.length}
          percentage="100%"
          trend={{ text: "Resume Inventory", positive: true }}
          active={activeDashboardFilter === "ALL"}
          onClick={() => {
            setActiveDashboardFilter("ALL");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<Sparkles size={19} />}
          label="Freshers"
          value={freshers}
          percentage={getPercentage(freshers)}
          trend={{ text: "Early Career", positive: true }}
          active={activeDashboardFilter === "FRESHERS"}
          onClick={() => {
            setActiveDashboardFilter("FRESHERS");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<Users size={19} />}
          label="Experienced"
          value={experienced}
          percentage={getPercentage(experienced)}
          trend={{ text: "Skilled Workforce", positive: true }}
          active={activeDashboardFilter === "EXPERIENCED"}
          onClick={() => {
            setActiveDashboardFilter("EXPERIENCED");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<UserCheck size={19} />}
          label="Verified"
          value={verified}
          percentage={getPercentage(verified)}
          trend={{ text: "Recruiter Verified", positive: true }}
          active={activeDashboardFilter === "VERIFIED"}
          onClick={() => {
            setActiveDashboardFilter("VERIFIED");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<AlertTriangle size={19} />}
          label="Needs review"
          value={needsReview}
          percentage={getPercentage(needsReview)}
          trend={{ text: "Screening Queue", positive: false }}
          active={activeDashboardFilter === "NEEDS_REVIEW"}
          onClick={() => {
            setActiveDashboardFilter("NEEDS_REVIEW");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<FileClock size={19} />}
          label="On hold"
          value={onHold}
          percentage={getPercentage(onHold)}
          trend={{ text: "Under Consideration", positive: false }}
          active={activeDashboardFilter === "ON_HOLD"}
          onClick={() => {
            setActiveDashboardFilter("ON_HOLD");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<CheckCircle2 size={19} />}
          label="Accepted"
          value={accepted}
          percentage={getPercentage(accepted)}
          trend={{ text: "Offer Stage", positive: true }}
          active={activeDashboardFilter === "ACCEPTED"}
          onClick={() => {
            setActiveDashboardFilter("ACCEPTED");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<AlertTriangle size={19} />}
          label="Rejected"
          value={rejected}
          percentage={getPercentage(rejected)}
          trend={{ text: "Closed Profile", positive: false }}
          active={activeDashboardFilter === "REJECTED"}
          onClick={() => {
            setActiveDashboardFilter("REJECTED");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<FileClock size={19} />}
          label="Pending candidates"
          value={pending}
          percentage={getPercentage(pending)}
          trend={{ text: "Awaiting Decision", positive: true }}
          active={activeDashboardFilter === "PENDING"}
          onClick={() => {
            setActiveDashboardFilter("PENDING");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<Target size={19} />}
          label="Marked for Interview"
          value={interviewMarkedCount}
          percentage={getPercentage(interviewMarkedCount)}
          trend={{ text: "Interview Stage", positive: true }}
          active={activeDashboardFilter === "INTERVIEW"}
          onClick={() => {
            setActiveDashboardFilter("INTERVIEW");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<Users size={19} />}
          label="Internal Candidates"
          value={internalCount}
          percentage={getPercentage(internalCount)}
          trend={{ text: "Internal Employees", positive: true }}
          active={activeDashboardFilter === "INTERNAL"}
          onClick={() => {
            setActiveDashboardFilter("INTERNAL");
            setSearchTerm("");
          }}
        />
        <Metric
          icon={<Globe size={19} />}
          label="External Candidates"
          value={externalCount}
          percentage={getPercentage(externalCount)}
          trend={{ text: "Market Talent", positive: true }}
          active={activeDashboardFilter === "EXTERNAL"}
          onClick={() => {
            setActiveDashboardFilter("EXTERNAL");
            setSearchTerm("");
          }}
        />
      </section>

      <section className="panel">
        <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", flexWrap: "wrap", marginBottom: "16px" }}>
          <div>
            <h3>{tableTitle}</h3>
            <span>Candidates in this category.</span>
          </div>
          <div className="search-bar-container" style={{ position: "relative", minWidth: "260px" }}>
            <input
              type="text"
              placeholder="Search within filter..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="dashboard-search-input"
              style={{
                width: "100%",
                padding: "8px 12px",
                paddingLeft: "34px",
                border: "1px solid #cbd5e1",
                borderRadius: "6px",
                fontSize: "0.88rem",
                outline: "none",
                transition: "border-color 0.2s ease"
              }}
            />
            <Search size={15} style={{ position: "absolute", left: "11px", top: "50%", transform: "translateY(-50%)", color: "#64748b" }} />
          </div>
        </div>
        {filteredCandidates.length ? (
          <Table columns={columns} rows={filteredCandidates} getRowKey={(row, index) => row.id || String(index)} />
        ) : (
          <EmptyState
            icon={<FileText size={26} />}
            title="No candidates found."
            description="There are currently no candidates in this category."
          />
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

function Metric({
  icon,
  label,
  value,
  percentage,
  trend,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  percentage?: string;
  trend?: { text: string; positive: boolean };
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <article
      className={`metric-tile interactive ${active ? "active" : ""}`}
      onClick={onClick}
      style={{ cursor: "pointer", display: "flex", flexDirection: "column", gap: "6px" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
        <div className="metric-icon-container" style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "32px", height: "32px", borderRadius: "6px", backgroundColor: active ? "#dbeafe" : "#f1f5f9", color: active ? "#2563eb" : "#64748b" }}>
          {icon}
        </div>
        {percentage && (
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#64748b", backgroundColor: "#f8fafc", padding: "2px 6px", borderRadius: "4px" }}>
            {percentage}
          </span>
        )}
      </div>
      <span style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: 500 }}>{label}</span>
      <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
        <strong style={{ fontSize: "1.5rem", fontWeight: 700, color: "#0f172a" }}>{value.toLocaleString()}</strong>
        {trend && (
          <span style={{ fontSize: "0.72rem", fontWeight: 600, padding: "2px 6px", borderRadius: "12px", display: "inline-flex", alignItems: "center", gap: "3px", backgroundColor: trend.positive ? "#ecfdf5" : "#fef2f2", color: trend.positive ? "#059669" : "#dc2626" }}>
            {trend.text}
          </span>
        )}
      </div>
    </article>
  );
}

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleDateString() : "-";
}
