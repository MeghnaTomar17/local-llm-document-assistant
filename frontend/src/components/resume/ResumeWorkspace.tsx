import { CalendarDays, Check, Download, Eye, FileText, Mail, MapPin, MessageSquare, PencilLine, Phone, Pin, Save, Send, UserRound, X } from "lucide-react";
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
  ["Technical Skills", "Show technical skills from the resume."],
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
  const [savingDecision, setSavingDecision] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!resume.session_id) return;
    setLoadingChat(true);
    getChatHistory(resume.session_id, resume.id)
      .then(setMessages)
      .catch((err) => setError(getApiError(err)))
      .finally(() => setLoadingChat(false));
  }, [resume.session_id, resume.id]);

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
    setError("");

    try {
      const response = await askResumeQuestion(trimmed, resume.session_id, resume.id);
      setMessages((current) => [...current, response.message]);
    } catch (err) {
      setError(getApiError(err));
      setMessages((current) => current.filter((message) => message !== userMessage));
    } finally {
      setAsking(false);
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
          <button className="btn btn-secondary" type="button" onClick={() => setPreviewOpen((current) => !current)}>
            <Eye size={16} />
            <span>{previewOpen ? "Hide Preview" : "Preview"}</span>
          </button>
          <a className="btn btn-secondary" href={getResumeDownloadUrl(resume.id)} target="_blank" rel="noreferrer">
            <Download size={16} />
            <span>Download</span>
          </a>
          <div className="decision-actions">
            <span>{decisionLabel(resume.hr_decision)}</span>
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
          </div>
        </div>
      </div>

      {isDocx(resume.mime_type || resume.original_file_name) && (
        <div className="info-banner">
          DOCX preview depends on browser support. Use Download if the preview opens blank.
        </div>
      )}

      {previewOpen && (
        <div className="resume-preview-panel">
          {isPdf(resume.mime_type || resume.original_file_name) ? (
            <iframe title="Resume preview" src={getResumePreviewUrl(resume.id)} />
          ) : (
            <EmptyState
              icon={<FileText size={24} />}
              title="Preview is not available for this file type."
              description="DOCX preview support depends on the browser. Download the resume to view it locally."
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
      onNotify(`Candidate ${decision.toLowerCase()}.`);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setSavingDecision(false);
    }
  }
}

function DecisionBadge({ decision }: { decision?: HRDecision | null }) {
  const value = decision || "PENDING";
  if (value === "ACCEPTED") return <Badge tone="success">Accepted</Badge>;
  if (value === "REJECTED") return <Badge tone="danger">Rejected</Badge>;
  return <Badge tone="warning">Pending Review</Badge>;
}

function decisionLabel(decision?: HRDecision | null) {
  if (decision === "ACCEPTED") return "Accepted";
  if (decision === "REJECTED") return "Rejected";
  return "Pending Review";
}

function isDocx(value?: string | null) {
  const text = String(value || "").toLowerCase();
  return text.includes("wordprocessingml") || text.endsWith(".docx");
}

function isPdf(value?: string | null) {
  const text = String(value || "").toLowerCase();
  return text.includes("pdf") || text.endsWith(".pdf");
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
}: {
  messages: ChatMessage[];
  loading: boolean;
  asking: boolean;
  question: string;
  setQuestion: (value: string) => void;
  onAsk: (text?: string) => void;
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
        {asking && <Loader label="Thinking" />}
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
    notes: resume.notes || "",
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
      notes: resume.notes || "",
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
  const [notes, setNotes] = useState(resume.notes || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const isDirty = notes !== (resume.notes || "");
  const [saveStatus, setSaveStatus] = useState("Saved");

  useEffect(() => {
    setNotes(resume.notes || "");
    setError("");
    setSaveStatus("Saved");
  }, [resume.id, resume.updated_at]);

  useEffect(() => {
    if (!isDirty) {
      setSaveStatus("Saved");
      return;
    }

    setSaveStatus("Autosaving...");
    const timer = window.setTimeout(() => {
      updateResume(resume.id as UUID, { notes })
        .then(async (updated) => {
          await onSaved(updated);
          setSaveStatus("Saved");
        })
        .catch((err) => {
          setError(getApiError(err));
          setSaveStatus("Autosave failed");
        });
    }, 900);

    return () => window.clearTimeout(timer);
  }, [isDirty, notes, resume.id, onSaved]);

  async function save() {
    setSaving(true);
    setError("");
    try {
      setSaveStatus("Saving...");
      await onSaved(await updateResume(resume.id as UUID, { notes }));
      setSaveStatus("Saved");
    } catch (err) {
      setError(getApiError(err));
      setSaveStatus("Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="edit-form">
      <p className="helper-text span-2">Keep private notes and observations for future reference.</p>
      {error && <div className="error-banner">{error}</div>}
      <label>Recruiter Notes<textarea className="notes-editor" rows={14} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
      <div className="notes-meta">
        <span>{saveStatus}</span>
        <span>{notes.length.toLocaleString()} characters</span>
      </div>
      <div className="form-actions">
        <Button variant="primary" icon={<MessageSquare size={16} />} disabled={saving} onClick={save}>{saving ? "Saving" : "Save Notes"}</Button>
      </div>
    </div>
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
