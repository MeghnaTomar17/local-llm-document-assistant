import { ChevronLeft, ChevronRight, History, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
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
  const { refresh, setNotice, updateResumeInState } = useAppData();
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [history, setHistory] = useState<SearchHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [searchStep, setSearchStep] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<ResumeDetail | null>(null);
  const [classificationFilter, setClassificationFilter] = useState<"ALL" | "INTERNAL" | "EXTERNAL">(() => {
    return (localStorage.getItem("search_classification_filter") as "ALL" | "INTERNAL" | "EXTERNAL") || "ALL";
  });

  const [elapsedTime, setElapsedTime] = useState(0);
  const [searchStage, setSearchStage] = useState(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(Math.max(textarea.scrollHeight, 72), 288)}px`;
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      runSearch();
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [query]);

  useEffect(() => {
    localStorage.setItem("search_classification_filter", classificationFilter);
  }, [classificationFilter]);

  const filteredResults = useMemo(() => {
    const results = response?.results || [];
    if (classificationFilter === "ALL") return results;
    return results.filter((row) => {
      const type = row.candidate_type || "EXTERNAL";
      if (classificationFilter === "INTERNAL") return type === "INTERNAL";
      if (classificationFilter === "EXTERNAL") return type === "EXTERNAL";
      return true;
    });
  }, [response?.results, classificationFilter]);

  const { page, pageCount, pageItems, setPage } = usePagination(filteredResults, 10);
  const showSkillComparison = !response?.no_searchable_criteria;

  const columns: TableColumn<SearchResult>[] = [
    { key: "candidate", header: "Candidate", className: "col-candidate", render: (row) => String(row.candidate_name || row.original_file_name || "Unnamed") },
    {
      key: "email",
      header: "Email",
      className: "col-email",
      render: (row) => (
        <span className="email-cell" title={row.email || ""}>
          {row.email || "-"}
        </span>
      )
    },
    { key: "phone", header: "Phone", className: "col-phone", render: (row) => row.phone_number || "-" },
    { key: "skills", header: "Skills", className: "col-skills", render: (row) => <SkillChips value={row.skills} /> },
    ...(showSkillComparison ? [
      { key: "matched_skills", header: "Matched Skills", className: "col-matched-skills", render: (row: SearchResult) => <SkillChips value={row.matched_skills} customClass="skill-chip-matched" /> },
      { key: "missing_skills", header: "Missing Skills", className: "col-missing-skills", render: (row: SearchResult) => <SkillChips value={row.missing_skills} customClass="skill-chip-missing" /> },
    ] : []),
    { key: "type", header: "Experience", className: "col-experience", render: (row) => <Badge tone={row.fresher ? "info" : "success"}>{row.fresher ? "Fresher" : "Experienced"}</Badge> },
    { key: "verified", header: "Verified", className: "col-verified", render: (row) => <Badge tone={row.is_verified ? "success" : "warning"}>{row.is_verified ? "Yes" : "Review"}</Badge> },
    { key: "decision", header: "Decision", className: "col-decision", render: (row) => <DecisionBadge decision={row.hr_decision} /> },
    { key: "interview", header: "Interview", className: "col-interview", render: (row) => row.interview_marked ? <Badge tone="success">Marked</Badge> : "-" },
    { key: "classification", header: "Classification", className: "col-classification", render: (row) => (
      <Badge tone={row.candidate_type === "INTERNAL" ? "success" : "info"}>
        {row.candidate_type === "INTERNAL" ? "Internal" : "External"}
      </Badge>
    ) },
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

  async function runSearch(overrideQuery?: string) {
    const trimmed = (overrideQuery !== undefined ? overrideQuery : query).trim();
    if (!trimmed || loading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    setLoading(true);
    setElapsedTime(0);
    setSearchStage(1);
    setError("");
    setSelected(null);

    const startTime = Date.now();
    const elapsedInterval = window.setInterval(() => {
      setElapsedTime(Number(((Date.now() - startTime) / 1000).toFixed(1)));
    }, 100);

    const stageInterval = window.setInterval(() => {
      setSearchStage((prev) => {
        const next = prev + 1;
        return Math.min(next, 5);
      });
    }, 1200);

    try {
      const responseData = await recruiterSearch(trimmed, null, "ALL", signal);
      setResponse(responseData);
      setPage(1);
      if (responseData.no_searchable_criteria) {
        setNotice(
          classificationFilter === "ALL"
            ? "No searchable skills or criteria were detected. Showing all candidate records."
            : "No searchable skills or criteria were detected. Showing all candidates from the selected pool.",
        );
      }
      await loadHistory();
    } catch (err: any) {
      if (err.name !== "CanceledError" && err.name !== "AbortError" && err.message !== "canceled") {
        setError(getApiError(err));
      }
    } finally {
      window.clearInterval(elapsedInterval);
      window.clearInterval(stageInterval);
      setLoading(false);
      setSearchStep("");
      abortControllerRef.current = null;
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
      results: item.results_snapshot,
      model_used: item.model_used,
      requirement_analysis: {},
      no_searchable_criteria: item.no_searchable_criteria || false,
    });
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
          <div className="search-filter-row">
            <span className="search-filter-label">Candidate Classification Pool:</span>
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
          {query.length > 4000 && (
            <div className="warning-banner">
              Long requirement detected. Less important sections will be trimmed automatically.
            </div>
          )}
          <form
            className="search-form"
            onSubmit={(event) => {
              event.preventDefault();
              runSearch();
            }}
          >
            <div className="textarea-container">
              <textarea
                ref={textareaRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={"Paste the complete job description or hiring requirements here...\n\nExample:\nLooking for a GIS Developer with ArcGIS Enterprise, ArcPy, Python, PostGIS, REST APIs, React, Docker and 3+ years of experience..."}
                disabled={loading}
              />
              <div className="char-counter-row">
                <span className={`char-counter ${query.length > 4000 ? "warning" : ""}`}>
                  {query.length} characters {query.length > 4000 ? "/ Long description will be prioritized" : ""}
                </span>
              </div>
            </div>
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
      {loading && <SearchLoadingState currentStage={searchStage} elapsed={elapsedTime} />}

      {response && !loading && (
        <>
          <div className="search-stats-banner">
            <div>
              <span>Requirements Analyzed</span>
              <strong>Yes</strong>
            </div>
            <div>
              <span>Candidates Matched</span>
              <strong>{response.row_count}</strong>
            </div>
            <div>
              <span>Execution Time</span>
              <strong>{((response.execution_time_ms || 0) / 1000).toFixed(2)}s</strong>
            </div>
            <div>
              <span>Results Returned</span>
              <strong>{filteredResults.length}</strong>
            </div>
            <div>
              <span>Candidate Pool</span>
              <strong className="search-stat-value">
                {classificationFilter.toLowerCase()}
              </strong>
            </div>
          </div>

          <RequirementAnalysis response={response} />

          <section className="panel">
            <div className="section-title">
              <h3>Results</h3>
              <span>{response.row_count} matches{response.execution_time_ms ? ` in ${response.execution_time_ms} ms` : ""}</span>
            </div>
            {filteredResults.length ? (
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
              <div className="empty-state-container" style={{ padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <EmptyState
                  title="No candidates satisfy all requested criteria."
                />
                {(() => {
                  const mandatorySkills = response?.requirement_analysis?.mandatory_skills;
                  const skillsList = Array.isArray(mandatorySkills)
                    ? mandatorySkills.map((item) => String(item).trim()).filter(Boolean)
                    : [];
                  if (skillsList.length === 0) return null;
                  return (
                    <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.88rem', color: '#647184', fontWeight: 500 }}>Mandatory skills searched:</span>
                      <div className="skill-chip-list" style={{ justifyContent: 'center' }}>
                        {skillsList.map((skill) => (
                          <span className="skill-chip skill-chip-missing" key={skill}>
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
          </section>
        </>
      )}

      <ResumeDetailsPanel
        resume={selected}
        onClose={() => setSelected(null)}
        onSaved={async (resume) => {
          setSelected(resume);
          setResponse((current) => updateSearchResponse(current, resume));
          setHistory((current) => updateSearchHistory(current, resume));
          updateResumeInState(resume);
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
        interview_marked: resume.interview_marked,
        candidate_type: resume.candidate_type,
      };
    }),
  };
}

function updateSearchHistory(current: SearchHistoryItem[], resume: ResumeDetail): SearchHistoryItem[] {
  return current.map((item) => {
    return {
      ...item,
      results_snapshot: item.results_snapshot.map((row) => {
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
          interview_marked: resume.interview_marked,
          candidate_type: resume.candidate_type,
        };
      }),
    };
  });
}

function DecisionBadge({ decision }: { decision?: string | null }) {
  if (decision === "ACCEPTED") return <Badge tone="success">Accepted</Badge>;
  if (decision === "REJECTED") return <Badge tone="danger">Rejected</Badge>;
  if (decision === "ON_HOLD") return <Badge tone="info">On Hold</Badge>;
  return <Badge tone="warning">Pending</Badge>;
}

function SearchLoadingState({ currentStage, elapsed }: { currentStage: number; elapsed: number }) {
  const stages = [
    { id: 1, label: "Cleaning requirements..." },
    { id: 2, label: "Extracting hiring criteria..." },
    { id: 3, label: "Generating SQL..." },
    { id: 4, label: "Searching database..." },
    { id: 5, label: "Preparing results..." },
  ];

  return (
    <section className="panel search-loading-panel fade-in" aria-busy="true">
      <div className="loader-stage-container" style={{ display: "flex", flexDirection: "column", gap: "8px", padding: "16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", alignItems: "center" }}>
          <strong style={{ fontSize: "1rem", color: "#1e293b" }}>Searching candidates...</strong>
          <span className="loader-stage-elapsed" style={{ fontSize: "0.85rem", color: "#647184" }}>{elapsed}s elapsed</span>
        </div>
        <div className="search-stages-list" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {stages.map((stage) => {
            const isCompleted = currentStage > stage.id;
            const isCurrent = currentStage === stage.id;
            
            let statusIcon = "○";
            let statusColor = "#94a3b8";
            let fontWeight = "normal";
            if (isCompleted) {
              statusIcon = "✓";
              statusColor = "#10b981";
            } else if (isCurrent) {
              statusIcon = "●";
              statusColor = "#3b82f6";
              fontWeight = "bold";
            }
            
            return (
              <div key={stage.id} style={{ display: "flex", alignItems: "center", gap: "10px", color: isCurrent ? "#1e293b" : "#647184", fontWeight }}>
                <span style={{ color: statusColor, fontSize: "1.1rem", width: "20px" }}>{statusIcon}</span>
                <span>{stage.label}</span>
              </div>
            );
          })}
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

function RequirementAnalysis({ response }: { response: SearchResponse }) {
  const analysis = response.requirement_analysis || {};
  const rows = [
    ["Mandatory Skills", listValue(analysis.mandatory_skills)],
    ["Preferred Skills", listValue(analysis.preferred_skills)],
    ["GIS Skills", listValue(analysis.gis_skills)],
    ["Experience", experienceValue(analysis.experience)],
    ["Cities", listValue(analysis.cities || analysis.locations)],
    ["Candidate Type", textValue(analysis.candidate_type)],
    ["Education", listValue(analysis.education)],
  ].filter(([, value]) => value !== "-");

  return (
    <section className="panel requirement-analysis-panel">
      <div className="section-title">
        <h3>Requirement Analysis</h3>
        <span>{rows.length ? "Extracted from recruiter input" : "No specific filters extracted"}</span>
      </div>
      {rows.length > 0 && (
        <div className="requirement-grid">
          {rows.map(([label, value]) => (
            <div className="requirement-item" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      )}

    </section>
  );
}

function listValue(value: unknown): string {
  if (Array.isArray(value)) {
    const items = value.map((item) => String(item).trim()).filter(Boolean);
    return items.length ? items.join(", ") : "-";
  }
  return textValue(value);
}

function textValue(value: unknown): string {
  const text = String(value ?? "").trim();
  return text || "-";
}

function experienceValue(value: unknown): string {
  if (!value || typeof value !== "object") return "-";
  const experience = value as Record<string, unknown>;
  const minimum = experience.minimum_years || experience.minimum;
  const maximum = experience.maximum_years || experience.maximum;
  if (minimum && maximum) return `${minimum}-${maximum} years`;
  if (minimum) return `${minimum}+ years`;
  if (maximum) return `Up to ${maximum} years`;
  return "-";
}

function SkillChips({ value, customClass }: { value: unknown; customClass?: string }) {
  const skills = normalizeSkills(value);
  if (!skills.length) return "-";

  return (
    <div className="skill-chip-list">
      {skills.map((skill, index) => (
        <span className={`skill-chip ${customClass || ""}`} key={`${skill}-${index}`}>
          {skill}
        </span>
      ))}
    </div>
  );
}

function normalizeSkills(value: unknown): string[] {
  let list: string[] = [];
  if (Array.isArray(value)) {
    list = value.map((item) => String(item).trim()).filter(Boolean);
  } else if (typeof value === "string") {
    list = value.split(",").map((item) => item.trim()).filter(Boolean);
  } else {
    return [];
  }

  const splitList: string[] = [];
  list.forEach((item) => {
    const cleaned = item
      .replace(/\s*&\s*/g, ",")
      .replace(/\s+\band\b\s+/gi, ",")
      .replace(/\s*\/\s*/g, ",")
      .replace(/\s*\\\s*/g, ",")
      .replace(/\s*\+\s*/g, ",");
    
    cleaned.split(",").forEach((part) => {
      const trimmed = part.trim();
      if (trimmed) {
        if (trimmed.toUpperCase() === "JS") {
          splitList.push("JavaScript");
        } else {
          splitList.push(trimmed);
        }
      }
    });
  });

  return Array.from(new Set(splitList));
}
