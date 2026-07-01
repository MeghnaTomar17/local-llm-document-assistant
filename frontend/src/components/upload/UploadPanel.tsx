import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import type { UUID } from "../../types";

export function UploadPanel({
  disabled,
  sessionId,
  onUpload,
}: {
  disabled?: boolean;
  sessionId?: UUID | null;
  onUpload: (files: File[], sessionId?: UUID | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  function submit(fileList: FileList | null) {
    const files = Array.from(fileList || []);
    if (files.length) onUpload(files, sessionId);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
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
        submit(event.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <UploadCloud size={28} />
      <strong>{disabled ? "Processing resumes" : "Drag & Drop Resume"}</strong>
      <span>{disabled ? "Preparing resumes for review." : "Upload one or multiple resumes in PDF or DOCX format."}</span>
      <input ref={inputRef} type="file" accept=".pdf,.docx" multiple disabled={disabled} onChange={(event) => submit(event.target.files)} />
    </section>
  );
}
