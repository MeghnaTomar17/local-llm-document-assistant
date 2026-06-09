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
  getChatHistory,
  getStats,
  uploadDocument,
} from "./services/api";
import "./styles.css";

const quickActions = [
  ["Summary", "Provide a detailed summary of this document."],
  ["Features", "List all key features and capabilities described."],
  ["Architecture", "Explain the system architecture described in the document."],
  ["Tech Stack", "List all technologies, frameworks, APIs, databases and tools mentioned."],
  ["Use Cases", "List all use cases and applications mentioned."],
  ["Future Scope", "List future enhancements and future scope discussed."],
];

function App() {
  const [stats, setStats] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [uploadNotice, setUploadNotice] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    refresh();
  }, []);

  async function refresh() {
    const [nextStats, nextMessages] = await Promise.all([getStats(), getChatHistory()]);
    setStats(nextStats);
    setMessages(nextMessages);
  }

  async function handleUpload(file) {
    if (!file) return;
    if (!/\.(pdf|doc|docx)$/i.test(file.name)) {
      setError("Upload a PDF, DOC, or DOCX file.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const hadPreviousDocument = Boolean(stats?.document_count);
      await uploadDocument(file);
      await refresh();
      setUploadNotice(
        hadPreviousDocument
          ? "New document detected. Previous document context has been cleared."
          : ""
      );
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
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
      await askQuestion(trimmed);
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
      await clearChat();
      setMessages([]);
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

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <FileText size={26} />
          <div>
            <h1>Local LLM</h1>
            <p>Document Assistant</p>
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
            handleUpload(event.dataTransfer.files[0]);
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <UploadCloud size={30} />
          <strong>Drop document</strong>
          <span>PDF, DOC, DOCX</span>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx"
            onChange={(event) => handleUpload(event.target.files[0])}
          />
        </section>

        <div className="quick-actions">
          {quickActions.map(([label, prompt]) => (
            <button key={label} disabled={!documents.length || busy} onClick={() => submitQuestion(prompt)}>
              <Sparkles size={16} />
              {label}
            </button>
          ))}
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h2>Document Intelligence</h2>
            <p>
              {activeDocument
                ? `Current Document: ${activeDocument.name}`
                : "Upload a document to start asking grounded questions."}
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
          <Stat icon={<FileText size={18} />} label="Documents" value={stats?.document_count || 0} />
          <Stat icon={<Layers size={18} />} label="Chunks" value={stats?.total_chunks || 0} />
          <Stat icon={<MessageSquare size={18} />} label="Messages" value={stats?.message_count || 0} />
          <Stat icon={<Clock size={18} />} label="Characters" value={(stats?.total_characters || 0).toLocaleString()} />
        </section>

        {activeDocument && (
          <details className="preview-panel">
            <summary>Extracted Document Preview</summary>
            <pre>{activeDocument.preview}</pre>
          </details>
        )}

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
              placeholder="Ask a follow-up question about the uploaded documents"
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
        {retrieval.chunk_count} chunks used | {retrieval.context_size.toLocaleString()} context chars | {promptSize?.toLocaleString()} prompt chars
      </summary>
      {retrieval.chunks.map((chunk) => (
        <div className="source" key={`${chunk.document_id}-${chunk.chunk_number}`}>
          <div>
            <strong>{chunk.document_name} | Chunk {chunk.chunk_number}</strong>
            <span>{chunk.section}</span>
          </div>
          <small>
            {chunk.size.toLocaleString()} chars | similarity {chunk.similarity?.toFixed(3) ?? "N/A"}
          </small>
          <p>{chunk.text.slice(0, 520)}</p>
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
