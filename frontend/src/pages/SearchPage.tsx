import { ChevronLeft, ChevronRight, History, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { ResumeDetailsPanel } from "../components/resume/ResumeDetailsPanel";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { SkeletonBlock, SkeletonRows } from "../components/ui/Skeleton";
import { Table, type TableColumn } from "../components/ui/Table";
import { usePagination } from "../hooks/usePagination";
import { useAppData } from "../context/AppContext";
import { getApiError } from "../services/http";
import { getResume } from "../services/resumeApi";
import { clearSearchHistory, deleteSearchHistoryItem, listSearchHistory, recruiterSearch } from "../services/searchApi";
import type { ResumeDetail, SearchHistoryItem, SearchResponse, SearchResult, UUID } from "../types";

export function SearchPage() {
  const { refresh, setNotice } = useAppData();
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [history, setHistory] = useState<SearchHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [searchStep, setSearchStep] = useState("");
  const [showHistory, setShowHistory] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<ResumeDetail | null>(null);
  const { page, pageCount, pageItems, setPage } = usePagination(response?.results || [], 10);

  const columns: TableColumn<SearchResult>[] = [
    { key: "candidate", header: "Candidate", className: "candidate-column", render: (row) => String(row.candidate_name || row.original_file_name || "Unnamed") },
    { key: "email", header: "Email", className: "email-column", render: (row) => String(row.email || "-") },
    { key: "phone", header: "Phone", className: "phone-column", render: (row) => String(row.phone_number || "-") },
    { key: "skills", header: "Skills", className: "skills-column", render: (row) => <SkillChips value={row.skills} /> },
    { key: "type", header: "Type", render: (row) => <Badge tone={row.fresher ? "info" : "success"}>{row.fresher ? "Fresher" : "Experienced"}</Badge> },
    { key: "verified", header: "Verified", render: (row) => <Badge tone={row.is_verified ? "success" : "warning"}>{row.is_verified ? "Yes" : "Review"}</Badge> },
    { key: "decision", header: "Decision", render: (row) => <DecisionBadge decision={row.hr_decision} /> },
  ];

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    setLoadingHistory(true);
    try {
      setHistory(await listSearchHistory());
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoadingHistory(false);
    }
  }

  async function runSearch() {
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setSearchStep("Searching candidates...");
    setError("");
    setSelected(null);
    const timer = window.setTimeout(() => setSearchStep("Finding matching resumes..."), 650);
    try {
      setResponse(await recruiterSearch(trimmed));
      setPage(1);
      await loadHistory();
    } catch (err) {
      setError(getApiError(err));
    } finally {
      window.clearTimeout(timer);
      setLoading(false);
      setSearchStep("");
    }
  }

  function restoreHistory(item: SearchHistoryItem) {
    if (loading) return;
    setQuery(item.query);
    setResponse({
      question: item.query,
      generated_sql: item.generated_sql,
      row_count: item.result_count,
      execution_time_ms: item.execution_time_ms,
      results: item.results_snapshot || [],
    });
    setPage(1);
  }

  async function openCandidate(row: SearchResult) {
    if (loading) return;
    const id = (row.id || row.resume_id) as UUID | undefined;
    if (!id) return;
    setNotice("");
    try {
      setSelected(await getResume(id));
    } catch (err) {
      setError(getApiError(err));
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Recruiter Search</h2>
          <p>Search resumes using simple questions to quickly find the right candidates.</p>
        </div>
        <Button
          icon={<History size={16} />}
          disabled={loading}
          onClick={() => setShowHistory((current) => !current)}
        >
          {showHistory ? "Hide History" : "Show History"}
        </Button>
      </header>

      <section className={`search-layout ${showHistory ? "" : "history-hidden"}`.trim()}>
        <div className="search-panel">
          <form
            className="search-form"
            onSubmit={(event) => {
              event.preventDefault();
              runSearch();
            }}
          >
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Example: Java developers in Bangalore with 2+ projects"
              disabled={loading}
            />
            <Button variant="primary" icon={<Search size={17} />} disabled={loading || !query.trim()}>
              {loading ? "Searching" : "Search"}
            </Button>
          </form>
        </div>
        {showHistory && (
          <aside className="history-panel">
            <div className="section-title">
              <h3><History size={16} /> Previous Searches</h3>
              {history.length > 0 && (
                <Button
                  variant="ghost"
                  icon={<Trash2 size={15} />}
                  disabled={loading || loadingHistory}
                  onClick={async () => {
                    await clearSearchHistory();
                    await loadHistory();
                  }}
                />
              )}
            </div>
            {loadingHistory && <SkeletonRows count={5} />}
            {!loadingHistory && !history.length && <EmptyState icon={<History size={24} />} title="No saved recruiter searches." description="Review your recent candidate searches." />}
            {!loadingHistory && history.map((item) => (
              <article className="history-item" key={item.id}>
                <button type="button" className="history-restore" disabled={loading} onClick={() => restoreHistory(item)}>
                  <strong>{item.query}</strong>
                  <span>{new Date(item.created_at).toLocaleString()}</span>
                  <small>{item.result_count} results</small>
                </button>
                <button
                  className="history-delete"
                  type="button"
                  title="Delete history item"
                  disabled={loading}
                  onClick={async (event) => {
                    event.stopPropagation();
                    await deleteSearchHistoryItem(item.id);
                    await loadHistory();
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </article>
            ))}
          </aside>
        )}
      </section>

      {error && <div className="error-banner">{error}</div>}
      {loading && <SearchLoadingState message={searchStep || "Searching candidates..."} />}

      {response && !loading && (
        <section className="panel">
          <div className="section-title">
            <h3>Results</h3>
            <span>{response.row_count} matches{response.execution_time_ms ? ` in ${response.execution_time_ms} ms` : ""}</span>
          </div>
          {response.generated_sql && (
            <details className="sql-panel">
              <summary>Generated SQL</summary>
              <pre>{response.generated_sql}</pre>
            </details>
          )}
          {response.results.length ? (
            <>
              <Table
                className="search-results-table"
                columns={columns}
                rows={pageItems}
                getRowKey={(row, index) => String(row.id || row.resume_id || index)}
                onRowClick={openCandidate}
              />
              <div className="pagination">
                <Button icon={<ChevronLeft size={16} />} disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
                <span>Page {page} of {pageCount}</span>
                <Button icon={<ChevronRight size={16} />} disabled={page >= pageCount} onClick={() => setPage(page + 1)}>Next</Button>
              </div>
            </>
          ) : (
            <EmptyState title="No matching candidates." />
          )}
        </section>
      )}

      <ResumeDetailsPanel
        resume={selected}
        onClose={() => setSelected(null)}
        onSaved={async (resume) => {
          setSelected(resume);
          setResponse((current) => updateSearchResponse(current, resume));
          await refresh();
          setNotice("Resume metadata updated successfully.");
        }}
      />
    </>
  );
}

function updateSearchResponse(current: SearchResponse | null, resume: ResumeDetail): SearchResponse | null {
  if (!current) return current;
  return {
    ...current,
    results: current.results.map((row) => {
      const rowId = row.id || row.resume_id;
      if (rowId !== resume.id) return row;
      return {
        ...row,
        candidate_name: resume.candidate_name,
        email: resume.email,
        phone_number: resume.phone_number,
        skills: resume.skills,
        cities: resume.cities,
        fresher: resume.fresher,
        is_verified: resume.is_verified,
        hr_decision: resume.hr_decision,
        decision_at: resume.decision_at,
        updated_at: resume.updated_at,
      };
    }),
  };
}

function DecisionBadge({ decision }: { decision?: string | null }) {
  if (decision === "ACCEPTED") return <Badge tone="success">Accepted</Badge>;
  if (decision === "REJECTED") return <Badge tone="danger">Rejected</Badge>;
  if (decision === "ON_HOLD") return <Badge tone="info">On Hold</Badge>;
  return <Badge tone="warning">Pending</Badge>;
}

function SearchLoadingState({ message }: { message: string }) {
  return (
    <section className="panel search-loading-panel fade-in" aria-busy="true">
      <div className="section-title">
        <div>
          <h3>Searching Candidates</h3>
          <span>{message}</span>
        </div>
        <div className="search-live-indicator">
          <span />
          <strong>{message}</strong>
        </div>
      </div>
      <div className="search-skeleton-table" aria-hidden="true">
        <div className="search-skeleton-head">
          {["Candidate", "Email", "Phone", "Skills", "Decision"].map((label) => (
            <SkeletonBlock className="search-skeleton-heading" key={label} />
          ))}
        </div>
        {Array.from({ length: 6 }).map((_, index) => (
          <div className="search-skeleton-row" key={index}>
            <SkeletonBlock className="skeleton-line skeleton-line-strong" />
            <SkeletonBlock className="skeleton-line skeleton-line-medium" />
            <SkeletonBlock className="skeleton-line skeleton-line-short" />
            <div className="search-skeleton-chips">
              <SkeletonBlock className="skeleton-pill" />
              <SkeletonBlock className="skeleton-pill" />
              <SkeletonBlock className="skeleton-pill" />
            </div>
            <SkeletonBlock className="skeleton-pill" />
          </div>
        ))}
      </div>
    </section>
  );
}

function SkillChips({ value }: { value: unknown }) {
  const skills = normalizeSkills(value);
  if (!skills.length) return "-";

  return (
    <div className="skill-chip-list">
      {skills.map((skill, index) => (
        <span className="skill-chip" key={`${skill}-${index}`}>
          {skill}
        </span>
      ))}
    </div>
  );
}

function normalizeSkills(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }

  if (typeof value === "string") {
    return value.split(",").map((item) => item.trim()).filter(Boolean);
  }

  return [];
}
