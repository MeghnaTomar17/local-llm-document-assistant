import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getApiError } from "../services/http";
import { listResumes } from "../services/resumeApi";
import { createSession, listSessionResumes, listSessions, switchSession, uploadResumes } from "../services/sessionApi";
import type { RecruiterSession, ResumeListItem, SessionsResponse, UUID, UploadResponse, UploadStatus } from "../types";

interface AppContextValue {
  resumes: ResumeListItem[];
  sessions: RecruiterSession[];
  activeSessionId: UUID | null;
  activeSessionResumes: ResumeListItem[];
  loading: boolean;
  busy: boolean;
  error: string;
  notice: string;
  duplicateWarning: UploadResponse | null;
  uploadStatus: UploadStatus;
  refresh: () => Promise<void>;
  setNotice: (notice: string) => void;
  clearDuplicateWarning: () => void;
  clearError: () => void;
  updateResumeInState: (resume: ResumeListItem) => void;
  handleCreateSession: (title?: string) => Promise<void>;
  handleSwitchSession: (sessionId: UUID) => Promise<void>;
  handleUpload: (files: File[], sessionId?: UUID | null) => Promise<void>;
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
  const [duplicateWarning, setDuplicateWarning] = useState<UploadResponse | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    active: false,
    total: 0,
    current: 0,
    step: "",
    progress: null,
  });

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

  async function handleCreateSession(title?: string) {
    setBusy(true);
    setError("");
    try {
      const response = await createSession(title);
      const sessionId = response.active_session_id || response.session?.session_id || response.session?.id;
      if (sessionId) {
        setActiveSessionId(sessionId);
        setNotice("Session created.");
      }
      await refresh();
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setBusy(false);
    }
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

  async function handleUpload(files: File[], sessionId: UUID | null = activeSessionId) {
    const validFiles = files.filter((file) => /\.(pdf|docx)$/i.test(file.name));
    const skipped = files.length - validFiles.length;
    if (!validFiles.length) {
      setError("Upload PDF or DOCX resumes.");
      return;
    }

    setBusy(true);
    setError("");
    setUploadStatus({
      active: true,
      total: validFiles.length,
      current: validFiles.length ? 1 : 0,
      currentFile: validFiles[0]?.name,
      step: "Uploading Resume...",
      progress: validFiles.length > 1 ? 8 : null,
    });
    try {
      window.setTimeout(() => setUploadStatus((current) => current.active ? { ...current, step: "Extracting Metadata...", progress: 26 } : current), 500);
      window.setTimeout(() => setUploadStatus((current) => current.active ? { ...current, step: "Generating Resume Chunks...", progress: 48 } : current), 1300);
      window.setTimeout(() => setUploadStatus((current) => current.active ? { ...current, step: "Building Embeddings...", progress: 66 } : current), 2100);
      window.setTimeout(() => setUploadStatus((current) => current.active ? { ...current, step: "Saving to Database...", progress: 82 } : current), 2900);
      window.setTimeout(() => setUploadStatus((current) => current.active ? { ...current, step: "Creating Recruiter Session...", progress: 92 } : current), 3600);
      const response = await uploadResumes(validFiles, sessionId);
      setUploadStatus((current) => ({ ...current, step: "Done", progress: 100 }));
      if (response.duplicate) {
        setDuplicateWarning(response);
        return;
      }
      const nextSessionId = response.session_id || response.active_session_id || sessionId || null;
      setActiveSessionId(nextSessionId);
      await refresh();
      const failed = response.errors?.length ? ` ${response.errors.length} file(s) failed.` : "";
      const skippedText = skipped ? ` ${skipped} unsupported file(s) skipped.` : "";
      setNotice(`${response.message || "Upload complete."}${skippedText}${failed}`);
      if (response.errors?.length) {
        setError(response.errors.map((item) => `${item.file_name}: ${item.error}`).join("\n"));
      }
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setBusy(false);
      window.setTimeout(() => {
        setUploadStatus({ active: false, total: 0, current: 0, step: "", progress: null });
      }, 700);
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
      duplicateWarning,
      uploadStatus,
      refresh,
      setNotice,
      clearDuplicateWarning: () => setDuplicateWarning(null),
      clearError: () => setError(""),
      updateResumeInState,
      handleCreateSession,
      handleSwitchSession,
      handleUpload,
    }),
    [resumes, sessions, activeSessionId, activeSessionResumes, loading, busy, error, notice, duplicateWarning, uploadStatus],
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
