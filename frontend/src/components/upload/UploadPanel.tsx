import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import type { UUID, UploadStatus } from "../../types";

export function UploadPanel({
  disabled,
  sessionId,
  onUpload,
  status,
}: {
  disabled?: boolean;
  sessionId?: UUID | null;
  onUpload: (files: File[], sessionId?: UUID | null) => void;
  status?: UploadStatus;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  function submit(fileList: FileList | null) {
    if (disabled) return;
    const files = Array.from(fileList || []);
    if (files.length) onUpload(files, sessionId);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <section
      className={`upload-zone ${dragging ? "is-dragging" : ""}`}
      aria-disabled={disabled ? "true" : "false"}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        if (disabled) return;
        submit(event.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <UploadCloud size={28} />
      <strong>{disabled ? status?.step || "Processing resumes" : "Drag & Drop Resume"}</strong>
      <span>
        {disabled && (status?.total || 0) > 1
          ? `Processing Resume ${status.current} of ${status.total}${status.currentFile ? `: ${status.currentFile}` : ""}`
          : disabled
            ? "Preparing resumes for review."
            : "Upload one or multiple resumes in PDF or DOCX format."}
      </span>
      {disabled && (
        <div className="upload-progress">
          <div className="progress-track">
            <div
              className={`progress-bar ${status?.progress == null ? "is-indeterminate" : ""}`}
              style={status?.progress != null ? { width: `${status.progress}%` } : undefined}
            />
          </div>
          <small>{status?.progress != null ? `${Math.round(status.progress)}%` : "Working..."}</small>
        </div>
      )}
      <input ref={inputRef} type="file" accept=".pdf,.docx" multiple disabled={disabled} onChange={(event) => submit(event.target.files)} />
    </section>
  );
}
