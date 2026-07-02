import { Download, Save, X } from "lucide-react";
import { useEffect, useState } from "react";
import { getResumeDownloadUrl, updateResume } from "../../services/resumeApi";
import { getApiError } from "../../services/http";
import type { ResumeDetail, ResumeUpdate, UUID } from "../../types";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";

function toCsv(values?: string[] | null) {
  return Array.isArray(values) ? values.join(", ") : "";
}

function fromCsv(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

export function ResumeDetailsPanel({
  resume,
  onClose,
  onSaved,
}: {
  resume: ResumeDetail | null;
  onClose: () => void;
  onSaved: (resume: ResumeDetail) => void | Promise<void>;
}) {
  const [form, setForm] = useState<ResumeUpdate>({});
  const [skills, setSkills] = useState("");
  const [cities, setCities] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!resume) return;
    setForm({
      candidate_name: resume.candidate_name || "",
      email: resume.email || "",
      phone_number: resume.phone_number || "",
      fresher: resume.fresher ?? null,
      hr_notes: resume.hr_notes || resume.notes || "",
      technical_notes: resume.technical_notes || "",
      final_notes: resume.final_notes || "",
    });
    setSkills(toCsv(resume.skills));
    setCities(toCsv(resume.cities));
    setError("");
  }, [resume]);

  if (!resume) return null;

  async function save() {
    if (!resume) return;
    setSaving(true);
    setError("");
    try {
      const updated = await updateResume(resume.id as UUID, {
        ...form,
        skills: fromCsv(skills),
        cities: fromCsv(cities),
      });
      await onSaved(updated);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <aside className="details-panel" aria-label="Resume details">
      <div className="panel-header">
        <div>
          <h2>{resume.candidate_name || "Candidate"}</h2>
          <p className="helper-text">Review and update extracted candidate information.</p>
          <div className="panel-badges">
            <Badge tone={resume.fresher ? "info" : "success"}>{resume.fresher ? "Fresher" : "Experienced"}</Badge>
            <Badge tone={resume.is_verified ? "success" : "warning"}>{resume.is_verified ? "Verified" : "Needs review"}</Badge>
          </div>
        </div>
        <Button variant="ghost" icon={<X size={18} />} onClick={onClose} title="Close" />
      </div>

      {error && <div className="error-banner">{error}</div>}

      <label>
        Candidate name
        <input value={form.candidate_name || ""} onChange={(event) => setForm({ ...form, candidate_name: event.target.value })} />
      </label>
      <label>
        Email
        <input value={form.email || ""} onChange={(event) => setForm({ ...form, email: event.target.value })} />
      </label>
      <label>
        Phone number
        <input value={form.phone_number || ""} onChange={(event) => setForm({ ...form, phone_number: event.target.value })} />
      </label>
      <label>
        Skills
        <textarea value={skills} onChange={(event) => setSkills(event.target.value)} rows={3} />
      </label>
      <label>
        Cities
        <input value={cities} onChange={(event) => setCities(event.target.value)} />
      </label>
      <label>
        Candidate type
        <select
          value={form.fresher === null || form.fresher === undefined ? "" : String(form.fresher)}
          onChange={(event) => setForm({ ...form, fresher: event.target.value === "" ? null : event.target.value === "true" })}
        >
          <option value="">Unclear</option>
          <option value="true">Fresher</option>
          <option value="false">Experienced</option>
        </select>
      </label>
      <label>
        HR Notes
        <textarea value={form.hr_notes || ""} onChange={(event) => setForm({ ...form, hr_notes: event.target.value })} rows={3} />
      </label>
      <label>
        Technical Notes
        <textarea value={form.technical_notes || ""} onChange={(event) => setForm({ ...form, technical_notes: event.target.value })} rows={3} />
      </label>
      <label>
        Final Notes
        <textarea value={form.final_notes || ""} onChange={(event) => setForm({ ...form, final_notes: event.target.value })} rows={3} />
      </label>

      <div className="panel-actions">
        <a className="btn btn-secondary" href={getResumeDownloadUrl(resume.id)} target="_blank" rel="noreferrer">
          <Download size={16} />
          <span>Download</span>
        </a>
        <Button variant="primary" icon={<Save size={16} />} onClick={save} disabled={saving}>
          {saving ? "Saving" : "Save"}
        </Button>
      </div>
    </aside>
  );
}
