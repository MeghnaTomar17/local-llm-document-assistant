import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { getApiError } from "../services/http";
import { getBulkImportStatus } from "../services/importApi";
import { listResumes } from "../services/resumeApi";
import { listSessionResumes, listSessions, switchSession } from "../services/sessionApi";
import type { BulkImportStatus, RecruiterSession, ResumeListItem, SessionsResponse, UUID } from "../types";

const BULK_IMPORT_STALE_TIMEOUT_MS = 100_000;

interface AppContextValue {
  resumes: ResumeListItem[];
  sessions: RecruiterSession[];
  activeSessionId: UUID | null;
  activeSessionResumes: ResumeListItem[];
  loading: boolean;
  busy: boolean;
  error: string;
  notice: string;
  bulkImportStatus: BulkImportStatus;
  sessionsLoaded: boolean;
  refresh: () => Promise<void>;
  refreshBulkImportStatus: () => Promise<BulkImportStatus | null>;
  setNotice: (notice: string) => void;
  clearError: () => void;
  updateResumeInState: (resume: ResumeListItem) => void;
  handleSwitchSession: (sessionId: UUID) => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [sessions, setSessions] = useState<RecruiterSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<UUID | null>(null);
  const [activeSessionResumes, setActiveSessionResumes] = useState<ResumeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [bulkImportStatus, setBulkImportStatus] = useState<BulkImportStatus>({
    running: false,
    processed: 0,
    total: 0,
    failed: 0,
    message: "No bulk import is running.",
  });
  const lastImportSignature = useRef("");
  const statusPollRef = useRef<number | null>(null);

  async function loadActiveSessionResumes(sessionId: UUID | null) {
    if (!sessionId) {
      setActiveSessionResumes([]);
      return;
    }
    const response = await listSessionResumes(sessionId);
    setActiveSessionResumes(response.resumes || []);
  }

  async function refresh() {
    setError("");
    setBusy(true);
    try {
      const [resumeData, sessionData] = await Promise.all([listResumes(), listSessions()]);
      setResumes(resumeData.resumes || []);
      setSessions(sessionData.sessions || []);
      const nextActive = sessionData.active_session_id || firstSessionId(sessionData) || null;
      setActiveSessionId(nextActive);
      await loadActiveSessionResumes(nextActive);
      setSessionsLoaded(true);
    } catch (err) {
      setError(getApiError(err));
      throw err;
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refresh().catch((err) => setError(getApiError(err))).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let cancelled = false;

    refreshBulkImportStatus().then((status) => {
      if (!cancelled && status?.running) startBulkStatusPolling();
    });

    function handleFocus() {
      refreshBulkImportStatus().then((status) => {
        if (status?.running) startBulkStatusPolling();
      });
    }

    window.addEventListener("focus", handleFocus);
    return () => {
      cancelled = true;
      window.removeEventListener("focus", handleFocus);
      stopBulkStatusPolling();
    };
  }, []);

  async function refreshBulkImportStatus(): Promise<BulkImportStatus | null> {
    try {
      const status = await getBulkImportStatus();
      setBulkImportStatus(status);

      const signature = `${status.running}:${status.processed}:${status.total}:${status.failed}:${status.updated_at || ""}`;
      const hasProgress = status.total > 0 && signature !== lastImportSignature.current;

      if (hasProgress) {
        lastImportSignature.current = signature;
        refresh().catch((err) => setError(getApiError(err)));
      }

      if (!status.running) {
        stopBulkStatusPolling();
      } else if (isBulkImportStale(status)) {
        stopBulkStatusPolling();
      }

      return status;
    } catch (err) {
      setError(getApiError(err));
      stopBulkStatusPolling();
      return null;
    }
  }

  function startBulkStatusPolling() {
    if (statusPollRef.current != null) return;
    statusPollRef.current = window.setInterval(() => {
      refreshBulkImportStatus().then((status) => {
        if (!status?.running) stopBulkStatusPolling();
      });
    }, 3000);
  }

  function stopBulkStatusPolling() {
    if (statusPollRef.current == null) return;
    window.clearInterval(statusPollRef.current);
    statusPollRef.current = null;
  }

  async function handleSwitchSession(sessionId: UUID) {
    if (sessionId === activeSessionId) return;
    setBusy(true);
    setError("");
    try {
      const result = await switchSession(sessionId);
      setActiveSessionId(result.active_session_id || sessionId);
      await refresh();
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setBusy(false);
    }
  }

  function updateResumeInState(resume: ResumeListItem) {
    setResumes((current) => current.map((item) => item.id === resume.id ? { ...item, ...resume } : item));
    setActiveSessionResumes((current) => current.map((item) => item.id === resume.id ? { ...item, ...resume } : item));
    setSessions((current) => current.map((session) => {
      const matchesResume = session.resume_id === resume.id || session.document?.resume_id === resume.id || session.session_id === resume.session_id;
      if (!matchesResume) return session;
      return {
        ...session,
        candidate_name: resume.candidate_name,
        original_file_name: resume.original_file_name,
        uploaded_at: resume.uploaded_at,
        hr_decision: resume.hr_decision,
        decision_at: resume.decision_at,
        title: resume.candidate_name || session.title,
        display_name: resume.candidate_name || session.display_name,
      };
    }));
  }

  const value = useMemo<AppContextValue>(
    () => ({
      resumes,
      sessions,
      activeSessionId,
      activeSessionResumes,
      loading,
      busy,
      error,
      notice,
      bulkImportStatus,
      sessionsLoaded,
      refresh: async () => {
        await refresh();
        const status = await refreshBulkImportStatus();
        if (status?.running) startBulkStatusPolling();
      },
      refreshBulkImportStatus,
      setNotice,
      clearError: () => setError(""),
      updateResumeInState,
      handleSwitchSession,
    }),
    [resumes, sessions, activeSessionId, activeSessionResumes, loading, busy, error, notice, bulkImportStatus, sessionsLoaded],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppData() {
  const value = useContext(AppContext);
  if (!value) throw new Error("useAppData must be used inside AppProvider");
  return value;
}

function firstSessionId(data: SessionsResponse): UUID | null {
  const first = data.sessions?.[0];
  return first?.session_id || first?.id || null;
}

function isBulkImportStale(status: BulkImportStatus) {
  const updatedAt = status.updated_at ? new Date(status.updated_at).getTime() : 0;
  return Boolean(status.running && updatedAt && Date.now() - updatedAt > BULK_IMPORT_STALE_TIMEOUT_MS);
}
