import { CalendarDays, Check, CirclePause, Download, Eye, FileText, Mail, MapPin, MessageSquare, PencilLine, Phone, Pin, Save, Send, UserRound, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { askResumeQuestion, getChatHistory } from "../../services/chatApi";
import { getApiError } from "../../services/http";
import { getResumeDownloadUrl, getResumePreviewUrl, updateResume } from "../../services/resumeApi";
import type { ChatMessage, HRDecision, ResumeDetail, ResumeUpdate, UUID } from "../../types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { EmptyState } from "../ui/EmptyState";
import { Loader } from "../ui/Loader";

type TabKey = "resume" | "chat" | "metadata" | "notes";

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "resume", label: "Resume" },
  { key: "chat", label: "Chat" },
  { key: "metadata", label: "Metadata" },
  { key: "notes", label: "Notes" },
];

const quickActions = [
  ["Summary", "Summarize the resume."],
  ["Contact", "Show contact information from the resume."],
  ["Skills", "Show skills from the resume."],
  ["Education", "Show education from the resume."],
  ["Experience", "Show experience from the resume."],
  ["Projects", "Show projects from the resume."],
  ["Certifications", "Show certifications from the resume."],
  ["Achievements", "Show achievements from the resume."],
  ["Language", "Show languages from the resume."],
];

export function ResumeWorkspace({
  resume,
  onResumeSaved,
  onNotify,
}: {
  resume: ResumeDetail;
  onResumeSaved: (resume: ResumeDetail) => Promise<void> | void;
  onNotify: (message: string) => void;
}) {
  const [tab, setTab] = useState<TabKey>("resume");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loadingChat, setLoadingChat] = useState(false);
  const [asking, setAsking] = useState(false);
  const [chatStep, setChatStep] = useState("");
  const [savingDecision, setSavingDecision] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [previewSrc, setPreviewSrc] = useState("");
  const [preparingDownload, setPreparingDownload] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!resume.session_id) return;
    setLoadingChat(true);
    getChatHistory(resume.session_id, resume.id)
      .then(setMessages)
      .catch((err) => setError(getApiError(err)))
      .finally(() => setLoadingChat(false));
  }, [resume.session_id, resume.id]);

  useEffect(() => {
    return () => {
      if (previewSrc.startsWith("blob:")) {
        URL.revokeObjectURL(previewSrc);
      }
    };
  }, [previewSrc]);

  async function ask(text = question) {
    const trimmed = text.trim();
    if (!trimmed || !resume.session_id || asking) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setAsking(true);
    setChatStep("Thinking...");
    setError("");
    const searchingTimer = window.setTimeout(() => setChatStep("Searching Resume..."), 500);
    const generatingTimer = window.setTimeout(() => setChatStep("Generating Response..."), 1200);

    try {
      const response = await askResumeQuestion(trimmed, resume.session_id, resume.id);
      setMessages((current) => [...current, response.message]);
    } catch (err) {
      setError(getApiError(err));
      setMessages((current) => current.filter((message) => message !== userMessage));
    } finally {
      window.clearTimeout(searchingTimer);
      window.clearTimeout(generatingTimer);
      setAsking(false);
      setChatStep("");
    }
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-heading">
        <div className="candidate-title">
          <span className="avatar-mark"><UserRound size={18} /></span>
          <div>
            <h3>{resume.candidate_name || resume.original_file_name || "Resume Workspace"}</h3>
            <p className="helper-text">Review candidate details, chat with the resume assistant, and update hiring decisions.</p>
            <div className="candidate-meta">
              <span><Mail size={14} /> {resume.email || "No email"}</span>
              <span><Phone size={14} /> {resume.phone_number || "No phone"}</span>
              <span><MapPin size={14} /> {(resume.cities || [])[0] || "No city"}</span>
              <span><CalendarDays size={14} /> {resume.uploaded_at ? new Date(resume.uploaded_at).toLocaleDateString() : "No upload date"}</span>
            </div>
            <div className="panel-badges">
              <Badge tone={resume.fresher ? "info" : "success"}>{resume.fresher ? "Fresher" : "Experienced"}</Badge>
              <Badge tone={resume.is_verified ? "success" : "warning"}>{resume.is_verified ? "Verified" : "Needs review"}</Badge>
              <DecisionBadge decision={resume.hr_decision} />
            </div>
          </div>
        </div>
        <div className="workspace-actions">
          <button
            className="btn btn-secondary"
            type="button"
            onClick={handlePreviewToggle}
          >
            <Eye size={16} />
            <span>{previewOpen ? "Hide Preview" : "Preview"}</span>
          </button>
          <a
            className={`btn btn-secondary ${preparingDownload ? "is-disabled" : ""}`}
            href={getResumeDownloadUrl(resume.id)}
            target="_blank"
            rel="noreferrer"
            onClick={() => {
              setPreparingDownload(true);
              window.setTimeout(() => setPreparingDownload(false), 900);
            }}
            aria-disabled={preparingDownload}
          >
            <Download size={16} />
            <span>{preparingDownload ? "Preparing Resume..." : "Download"}</span>
          </a>
          <div className="decision-actions">
            <span>{decisionLabel(resume.hr_decision)}</span>
            <Button
              icon={<CirclePause size={15} />}
              disabled={savingDecision || resume.hr_decision === "ON_HOLD"}
              onClick={() => saveDecision("ON_HOLD")}
            >
              On Hold
            </Button>
            <Button
              variant="primary"
              icon={<Check size={15} />}
              disabled={savingDecision || resume.hr_decision === "ACCEPTED"}
              onClick={() => saveDecision("ACCEPTED")}
            >
              Accept
            </Button>
            <Button
              variant="danger"
              icon={<X size={15} />}
              disabled={savingDecision || resume.hr_decision === "REJECTED"}
              onClick={() => saveDecision("REJECTED")}
            >
              Reject
            </Button>
            {savingDecision && <Loader label="Saving..." />}
          </div>
        </div>
      </div>

      {previewOpen && (
        <div className="resume-preview-panel">
          {canPreview(resume.mime_type || resume.original_file_name) ? (
            <>
              {previewLoading && <div className="preview-loading"><Loader label="Loading Resume Preview..." /></div>}
              {previewFailed ? (
                <EmptyState
                  icon={<FileText size={24} />}
                  title="Preview is unavailable for this document. You can still download the original file."
                  action={(
                    <a className="btn btn-secondary" href={getResumeDownloadUrl(resume.id)} target="_blank" rel="noreferrer">
                      <Download size={16} />
                      <span>Download Resume</span>
                    </a>
                  )}
                />
              ) : previewSrc ? (
                <iframe
                  title="Resume preview"
                  src={previewSrc}
                  onLoad={() => setPreviewLoading(false)}
                  onError={() => {
                    setPreviewLoading(false);
                    setPreviewFailed(true);
                  }}
                />
              ) : null}
            </>
          ) : (
            <EmptyState
              icon={<FileText size={24} />}
              title="Preview is not available for this file type."
              description="You can still download the original file."
              action={(
                <a className="btn btn-secondary" href={getResumeDownloadUrl(resume.id)} target="_blank" rel="noreferrer">
                  <Download size={16} />
                  <span>Download Resume</span>
                </a>
              )}
            />
          )}
        </div>
      )}

      <div className="tab-list">
        {tabs.map((item) => (
          <button key={item.key} className={tab === item.key ? "is-active" : ""} onClick={() => setTab(item.key)}>
            <TabIcon tab={item.key} />
            {item.label}
          </button>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {tab === "resume" && <ResumeTab resume={resume} />}
      {tab === "chat" && (
        <ChatTab
          messages={messages}
          loading={loadingChat}
          asking={asking}
          question={question}
          setQuestion={setQuestion}
          onAsk={ask}
          chatStep={chatStep}
        />
      )}
      {tab === "metadata" && (
        <MetadataForm
          resume={resume}
          onSaved={async (updated) => {
            await onResumeSaved(updated);
            onNotify("Resume metadata updated successfully.");
          }}
        />
      )}
      {tab === "notes" && (
        <NotesForm
          resume={resume}
          onSaved={async (updated) => {
            await onResumeSaved(updated);
            onNotify("Resume notes updated successfully.");
          }}
        />
      )}
    </section>
  );

  async function saveDecision(decision: HRDecision) {
    setSavingDecision(true);
    setError("");
    try {
      const updated = await updateResume(resume.id as UUID, { hr_decision: decision });
      await onResumeSaved(updated);
      onNotify(`Decision saved: ${decisionLabel(decision)}.`);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setSavingDecision(false);
    }
  }

  async function handlePreviewToggle() {
    if (previewOpen) {
      setPreviewOpen(false);
      setPreviewFailed(false);
      setPreviewLoading(false);
      setPreviewSrc("");
      return;
    }

    const fileType = resume.mime_type || resume.original_file_name;
    setPreviewOpen(true);
    setPreviewFailed(false);

    if (!canPreview(fileType)) {
      setPreviewLoading(false);
      return;
    }

    setPreviewLoading(true);
    const previewUrl = getResumePreviewUrl(resume.id);

    // Fetch the preview as a blob and use an object URL for the iframe.
    // This avoids browser-level PDF handlers prompting to download.
    try {
      const response = await fetch(previewUrl);
      if (!response.ok) throw new Error("Preview unavailable");
      const blob = await response.blob();
      setPreviewSrc(URL.createObjectURL(blob));
    } catch {
      setPreviewFailed(true);
      setPreviewLoading(false);
    }
  }
}

function DecisionBadge({ decision }: { decision?: HRDecision | null }) {
  const value = decision || "PENDING";
  if (value === "ACCEPTED") return <Badge tone="success">Accepted</Badge>;
  if (value === "REJECTED") return <Badge tone="danger">Rejected</Badge>;
  if (value === "ON_HOLD") return <Badge tone="info">On Hold</Badge>;
  return <Badge tone="warning">Pending</Badge>;
}

function decisionLabel(decision?: HRDecision | null) {
  if (decision === "ACCEPTED") return "Accepted";
  if (decision === "REJECTED") return "Rejected";
  if (decision === "ON_HOLD") return "On Hold";
  return "Pending";
}

function isDocx(value?: string | null) {
  const text = String(value || "").toLowerCase();
  return text.includes("wordprocessingml") || text.endsWith(".docx");
}

function isPdf(value?: string | null) {
  const text = String(value || "").toLowerCase();
  return text.includes("pdf") || text.endsWith(".pdf");
}

function canPreview(value?: string | null) {
  return isPdf(value) || isDocx(value);
}

function TabIcon({ tab }: { tab: TabKey }) {
  if (tab === "resume") return <FileText size={16} />;
  if (tab === "chat") return <MessageSquare size={16} />;
  if (tab === "metadata") return <PencilLine size={16} />;
  return <Pin size={16} />;
}

function ResumeTab({ resume }: { resume: ResumeDetail }) {
  return (
    <div className="resume-summary-grid">
      <Info label="Email" value={resume.email} />
      <Info label="Phone" value={resume.phone_number} />
      <Info label="Cities" value={(resume.cities || []).join(", ")} />
      <Info label="Skills" value={(resume.skills || []).join(", ")} />
      <Info label="File" value={resume.original_file_name} />
      <Info label="Uploaded" value={resume.uploaded_at ? new Date(resume.uploaded_at).toLocaleString() : "-"} />
    </div>
  );
}

function ChatTab({
  messages,
  loading,
  asking,
  question,
  setQuestion,
  onAsk,
  chatStep,
}: {
  messages: ChatMessage[];
  loading: boolean;
  asking: boolean;
  question: string;
  setQuestion: (value: string) => void;
  onAsk: (text?: string) => void;
  chatStep: string;
}) {
  return (
    <div className="chat-workspace">
      <p className="helper-text chat-helper">Ask questions about the selected candidate and receive instant insights from their resume.</p>
      <div className="example-row">
        {quickActions.map(([label, prompt]) => (
          <button key={label} onClick={() => onAsk(prompt)} disabled={loading || asking}>
            {label}
          </button>
        ))}
      </div>

      <div className="messages">
        {loading && <Loader label="Loading chat history" />}
        {!loading && !messages.length && <EmptyState title="No chat messages for this resume yet." />}
        {messages.map((message, index) => (
          <article className={`message ${message.role}`} key={`${message.timestamp}-${index}`}>
            <div className="message-meta">
              <span>{message.role === "assistant" ? "AI" : "You"}</span>
              <time>{message.timestamp ? new Date(message.timestamp).toLocaleString() : ""}</time>
            </div>
            <p>{message.content}</p>
            {message.role === "assistant" && (
              <div className="message-stats">
                {message.response_time && <small>{message.response_time.toFixed(2)}s</small>}
                <small>Llama 3.2</small>
                <small>{message.retrieval?.chunks?.length || 0} chunks</small>
              </div>
            )}
            {message.retrieval?.chunks?.length ? <Sources message={message} /> : null}
          </article>
        ))}
        {asking && <Loader label={chatStep || "Thinking..."} />}
      </div>

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          onAsk();
        }}
      >
        <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask anything about this resume..." disabled={asking} />
        <Button variant="primary" icon={<Send size={17} />} disabled={asking || !question.trim()} />
      </form>
    </div>
  );
}

function MetadataForm({ resume, onSaved }: { resume: ResumeDetail; onSaved: (resume: ResumeDetail) => Promise<void> }) {
  const [form, setForm] = useState<ResumeUpdate>({
    candidate_name: resume.candidate_name || "",
    email: resume.email || "",
    phone_number: resume.phone_number || "",
    fresher: resume.fresher ?? null,
  });
  const [skills, setSkills] = useState((resume.skills || []).join(", "));
  const [cities, setCities] = useState((resume.cities || []).join(", "));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const skillChips = useMemo(() => splitCsv(skills), [skills]);

  useEffect(() => {
    setForm({
      candidate_name: resume.candidate_name || "",
      email: resume.email || "",
      phone_number: resume.phone_number || "",
      fresher: resume.fresher ?? null,
    });
    setSkills((resume.skills || []).join(", "));
    setCities((resume.cities || []).join(", "));
    setError("");
  }, [resume.id, resume.updated_at]);

  async function save() {
    setSaving(true);
    setError("");
    try {
      const updated = await updateResume(resume.id as UUID, {
        ...form,
        skills: splitCsv(skills),
        cities: splitCsv(cities),
      });
      await onSaved(updated);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="edit-form">
      <p className="helper-text span-2">Review and update extracted candidate information.</p>
      {error && <div className="error-banner">{error}</div>}
      <label>Candidate Name<input value={form.candidate_name || ""} onChange={(event) => setForm({ ...form, candidate_name: event.target.value })} /></label>
      <label>Email<input value={form.email || ""} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
      <label>Phone Number<input value={form.phone_number || ""} onChange={(event) => setForm({ ...form, phone_number: event.target.value })} /></label>
      <label>Cities<input value={cities} onChange={(event) => setCities(event.target.value)} /></label>
      <label>
        Fresher Status
        <select
          value={form.fresher === null || form.fresher === undefined ? "" : String(form.fresher)}
          onChange={(event) => setForm({ ...form, fresher: event.target.value === "" ? null : event.target.value === "true" })}
        >
          <option value="">Unclear</option>
          <option value="true">Fresher</option>
          <option value="false">Experienced</option>
        </select>
      </label>
      <label className="span-2">Skills<textarea rows={3} value={skills} onChange={(event) => setSkills(event.target.value)} /></label>
      <div className="skill-chip-list span-2">
        {skillChips.length ? skillChips.map((skill, index) => <span className="skill-chip" key={`${skill}-${index}`}>{skill}</span>) : <span className="form-muted">No skills added</span>}
      </div>
      <div className="form-actions">
        <Button variant="primary" icon={<Save size={16} />} disabled={saving} onClick={save}>{saving ? "Saving" : "Save Metadata"}</Button>
      </div>
    </div>
  );
}

function NotesForm({ resume, onSaved }: { resume: ResumeDetail; onSaved: (resume: ResumeDetail) => Promise<void> }) {
  const legacyNotes = resume.hr_notes || resume.notes || "";
  const [error, setError] = useState("");

  return (
    <div className="edit-form">
      <p className="helper-text span-2">Keep private notes and observations for future reference.</p>
      {error && <div className="error-banner">{error}</div>}
      <NoteSection
        resumeId={resume.id as UUID}
        label="HR Notes"
        field="hr_notes"
        value={legacyNotes}
        onSaved={onSaved}
        onError={setError}
      />
      <NoteSection
        resumeId={resume.id as UUID}
        label="Technical Notes"
        field="technical_notes"
        value={resume.technical_notes || ""}
        onSaved={onSaved}
        onError={setError}
      />
      <NoteSection
        resumeId={resume.id as UUID}
        label="Final Notes"
        field="final_notes"
        value={resume.final_notes || ""}
        onSaved={onSaved}
        onError={setError}
      />
    </div>
  );
}

type NoteField = "hr_notes" | "technical_notes" | "final_notes";

function NoteSection({
  resumeId,
  label,
  field,
  value,
  onSaved,
  onError,
}: {
  resumeId: UUID;
  label: string;
  field: NoteField;
  value: string;
  onSaved: (resume: ResumeDetail) => Promise<void>;
  onError: (message: string) => void;
}) {
  const [text, setText] = useState(value);
  const [status, setStatus] = useState("Saved");
  const [saving, setSaving] = useState(false);
  const isDirty = text !== value;

  useEffect(() => {
    setText(value);
    setStatus("Saved");
  }, [resumeId, value]);

  useEffect(() => {
    if (!isDirty) {
      setStatus("Saved");
      return;
    }

    setStatus("Autosaving...");
    const timer = window.setTimeout(() => {
      persist();
    }, 900);

    return () => window.clearTimeout(timer);
  }, [isDirty, text, resumeId, field]);

  async function persist() {
    setSaving(true);
    onError("");
    try {
      const updated = await updateResume(resumeId, { [field]: text } as ResumeUpdate);
      await onSaved(updated);
      setStatus("Saved");
    } catch (err) {
      setStatus("Autosave failed");
      onError(getApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="note-section span-2">
      <label>
        {label}
        <textarea className="notes-editor" rows={6} value={text} onChange={(event) => setText(event.target.value)} />
      </label>
      <div className="notes-meta">
        <span>{status}</span>
        <span>{text.length.toLocaleString()} characters</span>
      </div>
      <div className="form-actions">
        <Button variant="primary" icon={<MessageSquare size={16} />} disabled={saving || !isDirty} onClick={persist}>
          {saving ? "Saving" : `Save ${label}`}
        </Button>
      </div>
    </section>
  );
}

function Sources({ message }: { message: ChatMessage }) {
  return (
    <details className="sources">
      <summary>Retrieved Sources ({message.retrieval?.chunks?.length || 0})</summary>
      {message.retrieval?.chunks?.map((chunk, index) => (
        <div className="source" key={index}>
          <strong>Chunk {String(chunk.chunk_number || index + 1)} · {String(chunk.document_name || chunk.title || chunk.section || "Source")}</strong>
          <p>{String(chunk.content || chunk.text || "").slice(0, 420)}</p>
        </div>
      ))}
    </details>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="info-cell">
      <span>{label}</span>
      <strong>{value || "-"}</strong>
    </div>
  );
}

function splitCsv(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}
