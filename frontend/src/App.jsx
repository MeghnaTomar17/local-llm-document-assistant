import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Clock,
  Download,
  FileText,
  Layers,
  MessageSquare,
  Send,
  Sparkles,
  Trash2,
  UploadCloud,
} from "lucide-react";
import {
  askQuestion,
  clearChat,
  getDebugData,
  getSessions,
  getChatHistory,
  getStats,
  resetRuntimeState,
  switchSession,
  uploadDocument,
  uploadDocuments,
} from "./services/api";
import "./styles.css";

const quickActions = [
  ["Resume Summary", "Summarize the resume."],
  ["Contact Information", "Show contact information from the resume."],
  ["Skills", "Show skills from the resume."],
  ["Technical Skills", "Show technical skills from the resume."],
  ["Education", "Show education from the resume."],
  ["Experience", "Show experience from the resume."],
  ["Projects", "Show projects from the resume."],
  ["Certifications", "Show certifications from the resume."],
  ["Achievements", "Show achievements from the resume."],
  ["Languages", "Show languages from the resume."],
  ["Career Highlights", "List the career highlights from the resume."],
  ["Recruiter Summary", "Write a concise recruiter summary using only the resume."],
];

function App() {
  const [stats, setStats] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [uploadNotice, setUploadNotice] = useState("");
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [debugMode, setDebugMode] = useState(false);
  const [debugData, setDebugData] = useState(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    refresh();
  }, []);

  async function refresh() {
    const [nextStats, nextMessages, sessionData] = await Promise.all([
      getStats(activeSessionId),
      getChatHistory(activeSessionId),
      getSessions(),
    ]);
    setStats(nextStats);
    setMessages(nextMessages);
    setSessions(sessionData.sessions || []);
    setActiveSessionId(nextStats.active_session_id || sessionData.active_session_id || null);
    if (debugMode) {
      const nextDebugData = await getDebugData(activeSessionId);
      setDebugData(nextDebugData);
    }
  }

  async function handleUpload(fileList) {
    const selectedFiles = Array.from(fileList || []);
    if (!selectedFiles.length) return;

    const validFiles = selectedFiles.filter((file) => /\.(pdf|docx)$/i.test(file.name));
    const invalidCount = selectedFiles.length - validFiles.length;

    if (!validFiles.length) {
      setError("Upload PDF or DOCX resumes.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const result = validFiles.length === 1
        ? await uploadDocument(validFiles[0])
        : await uploadDocuments(validFiles);
      setActiveSessionId(result.session_id);
      const [nextStats, nextMessages, sessionData] = await Promise.all([
        getStats(result.session_id),
        getChatHistory(result.session_id),
        getSessions(),
      ]);
      setStats(nextStats);
      setMessages(nextMessages);
      setSessions(sessionData.sessions || []);
      if (debugMode) {
        setDebugData(await getDebugData(result.session_id));
      }
      const rejectedMessage = invalidCount ? ` ${invalidCount} unsupported file(s) were skipped.` : "";
      const failedMessage = result.errors?.length ? ` ${result.errors.length} file(s) failed.` : "";
      setUploadNotice(`${result.message || "Resume upload complete."}${rejectedMessage}${failedMessage}`);
      if (result.errors?.length) {
        setError(result.errors.map((item) => `${item.file_name}: ${item.error}`).join("\n"));
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function submitQuestion(text = question) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;

    setBusy(true);
    setError("");
    setQuestion("");
    setMessages((current) => [
      ...current,
      { role: "user", content: trimmed, timestamp: new Date().toISOString() },
    ]);

    try {
      await askQuestion(trimmed, activeSessionId);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleClearChat() {
    setBusy(true);
    try {
      await clearChat(activeSessionId);
      setMessages([]);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function handleClearWorkspace() {
    if (busy) return;

    setBusy(true);
    setError("");
    try {
      await resetRuntimeState();
      setStats(null);
      setMessages([]);
      setSessions([]);
      setActiveSessionId(null);
      setDebugData(null);
      setQuestion("");
      setUploadNotice("Workspace cleared. Upload resumes to start a new session.");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  const exportText = useMemo(() => {
    return messages
      .map((message) => `[${message.timestamp || new Date().toISOString()}] ${message.role.toUpperCase()}\n${message.content}`)
      .join("\n\n");
  }, [messages]);

  const exportHref = useMemo(() => {
    return URL.createObjectURL(new Blob([exportText], { type: "text/plain" }));
  }, [exportText]);

  const documents = stats?.documents || [];
  const activeDocument = documents[documents.length - 1];

  async function handleSwitchSession(sessionId) {
    if (!sessionId || sessionId === activeSessionId || busy) return;

    setBusy(true);
    setError("");
    try {
      const result = await switchSession(sessionId);
      setActiveSessionId(result.active_session_id);
      setStats(result.stats);
      setMessages(result.messages || []);
      const sessionData = await getSessions();
      setSessions(sessionData.sessions || []);
      if (debugMode) {
        setDebugData(await getDebugData(result.active_session_id));
      }
      setUploadNotice("");
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <FileText size={26} />
          <div>
            <h1>Local LLM</h1>
            <p>Resume Intelligence</p>
          </div>
        </div>

        <section
          className={`upload-zone ${dragging ? "is-dragging" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            handleUpload(event.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <UploadCloud size={30} />
          <strong>Drop resumes</strong>
          <span>PDF, DOCX | single or multiple</span>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            multiple
            onChange={(event) => handleUpload(event.target.files)}
          />
        </section>

        <div className="workspace-actions">
          <button disabled={busy} onClick={handleClearWorkspace}>
            <Trash2 size={16} />
            Clear Workspace
          </button>
        </div>

        <div className="quick-actions">
          {quickActions.map(([label, prompt]) => (
            <button key={label} disabled={!documents.length || busy} onClick={() => submitQuestion(prompt)}>
              <Sparkles size={16} />
              {label}
            </button>
          ))}
        </div>

        {sessions.length > 0 && (
          <section className="session-list">
            <h2>Resume Sessions</h2>
            {sessions.map((session) => (
              <button
                key={session.session_id}
                className={session.session_id === activeSessionId ? "is-active" : ""}
                onClick={() => handleSwitchSession(session.session_id)}
                disabled={busy}
              >
                <FileText size={15} />
                <span title={session.display_name || session.document.name}>
                  {session.display_name || session.document.name}
                </span>
                <small>
                  {session.document_count || 1} resumes | {session.message_count} messages
                </small>
              </button>
            ))}
          </section>
        )}

        <label className="debug-toggle">
          <input
            type="checkbox"
            checked={debugMode}
            onChange={async (event) => {
              const enabled = event.target.checked;
              setDebugMode(enabled);
              setDebugData(enabled ? await getDebugData(activeSessionId) : null);
            }}
          />
          Developer debug mode
        </label>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h2>Resume Intelligence</h2>
            <p>
              {activeDocument
                ? `Current Resume: ${activeDocument.name}${documents.length > 1 ? ` (${documents.length} in session)` : ""}`
                : "Upload a resume to start asking grounded questions."}
            </p>
          </div>
          <div className="toolbar">
            <a className="icon-button" href={exportHref} download="local-llm-chat-export.txt" title="Export chat">
              <Download size={18} />
            </a>
            <button className="icon-button" onClick={handleClearChat} disabled={busy} title="Clear chat">
              <Trash2 size={18} />
            </button>
          </div>
        </header>

        {error && <div className="error-banner">{error}</div>}
        {uploadNotice && <div className="success-banner">{uploadNotice}</div>}

        <section className="stats-grid">
          <Stat icon={<FileText size={18} />} label="Resumes" value={stats?.document_count || 0} />
          <Stat icon={<Layers size={18} />} label="Chunks" value={stats?.total_chunks || 0} />
          <Stat icon={<MessageSquare size={18} />} label="Messages" value={stats?.message_count || 0} />
          <Stat icon={<Clock size={18} />} label="Characters" value={(stats?.total_characters || 0).toLocaleString()} />
        </section>

        {activeDocument && (
          <details className="preview-panel">
            <summary>Extracted Resume Preview ({documents.length} resume{documents.length === 1 ? "" : "s"})</summary>
            {documents.map((document) => (
              <div className="preview-document" key={document.document_id}>
                <h3>{document.name}</h3>
                <pre>{document.preview}</pre>
              </div>
            ))}
          </details>
        )}

        {debugMode && <DebugPanel data={debugData} />}

        <section className="chat-panel">
          <div className="messages">
            {!messages.length && <div className="empty-chat">Ask a question or choose a quick action.</div>}
            {messages.map((message, index) => (
              <article className={`message ${message.role}`} key={`${message.timestamp}-${index}`}>
                <div className="message-meta">
                  <span>{message.role}</span>
                  <time>{formatTime(message.timestamp)}</time>
                </div>
                <p>{message.content}</p>
                {message.response_time && <small>Generated in {message.response_time.toFixed(2)} seconds</small>}
                {message.retrieval && <SourceList retrieval={message.retrieval} promptSize={message.prompt_size} />}
              </article>
            ))}
          </div>

          <form
            className="composer"
            onSubmit={(event) => {
              event.preventDefault();
              submitQuestion();
            }}
          >
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a follow-up question about the active resume"
              disabled={busy}
            />
            <button disabled={busy || !question.trim()} title="Send">
              <Send size={18} />
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}

function DebugPanel({ data }) {
  if (!data) {
    return <section className="debug-panel">Debug data is not available yet.</section>;
  }

  return (
    <section className="debug-panel">
      <h2>Developer Debug</h2>
      <details>
        <summary>Extracted Text</summary>
        <pre>{data.extracted_text || ""}</pre>
      </details>
      <details>
        <summary>Generated Chunks ({data.chunks?.length || 0})</summary>
        <pre>{JSON.stringify(data.chunks || [], null, 2)}</pre>
      </details>
      <details>
        <summary>Chunk Metadata</summary>
        <pre>{JSON.stringify((data.chunks || []).map(({ content, ...metadata }) => metadata), null, 2)}</pre>
      </details>
      <details>
        <summary>Retrieved Chunks ({data.retrieved_chunks?.length || 0})</summary>
        <pre>{JSON.stringify(data.retrieved_chunks || [], null, 2)}</pre>
      </details>
      <details>
        <summary>Similarity Scores</summary>
        <pre>{JSON.stringify((data.retrieved_chunks || []).map((chunk) => ({
          chunk_id: chunk.chunk_id,
          section: chunk.section,
          title: chunk.title,
          page: chunk.page,
          similarity: chunk.similarity ?? "N/A",
          strategy: data.last_retrieval?.strategy,
        })), null, 2)}</pre>
      </details>
      <details>
        <summary>Final LLM Context</summary>
        <pre>{data.final_context || ""}</pre>
      </details>
    </section>
  );
}

function Stat({ icon, label, value }) {
  return (
    <div className="stat-card">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SourceList({ retrieval, promptSize }) {
  return (
    <details className="sources">
      <summary>
        Retrieved: {retrieval.chunks.map((chunk) => `${chunk.section} | Chunk ${chunk.chunk_number} | Page ${chunk.page || "N/A"}`).join("; ")}
      </summary>
      <div className="source-meta">
        {retrieval.chunk_count} chunks used | {retrieval.context_size.toLocaleString()} context chars | {promptSize?.toLocaleString()} prompt chars | {retrieval.strategy || "semantic"}
      </div>
      {retrieval.chunks.map((chunk) => (
        <div className="source" key={`${chunk.document_id}-${chunk.chunk_number}`}>
          <div>
            <strong>{chunk.document_name} | Chunk {chunk.chunk_number}</strong>
            <span>{chunk.section} | Chunk ID {chunk.chunk_id || chunk.chunk_number} | Page {chunk.page || "N/A"} | {chunk.title || chunk.section}</span>
          </div>
          <small>
            {chunk.size.toLocaleString()} chars | similarity {chunk.similarity?.toFixed(3) ?? "N/A"}
          </small>
          <p>{(chunk.content || chunk.text).slice(0, 520)}</p>
        </div>
      ))}
    </details>
  );
}

function formatTime(value) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

createRoot(document.getElementById("root")).render(<App />);


