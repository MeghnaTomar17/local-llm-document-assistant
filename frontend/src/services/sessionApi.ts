import { api } from "./http";
import type { RecruiterSession, ResumeListItem, SessionsResponse, UUID, UploadResponse } from "../types";

export async function listSessions(): Promise<SessionsResponse> {
  const response = await api.get<SessionsResponse>("/sessions");
  return response.data;
}

export async function createSession(title?: string): Promise<{
  active_session_id: UUID;
  session: RecruiterSession;
  sessions: RecruiterSession[];
}> {
  const response = await api.post("/sessions", title ? { title } : {});
  return response.data;
}

export async function switchSession(sessionId: UUID): Promise<{
  active_session_id: UUID;
  messages?: unknown[];
  stats?: unknown;
}> {
  const response = await api.post("/switch-session", { session_id: sessionId });
  return response.data;
}

export async function listSessionResumes(sessionId: UUID): Promise<{ session_id: UUID; resumes: ResumeListItem[] }> {
  const response = await api.get(`/sessions/${sessionId}/resumes`);
  return response.data;
}

export async function uploadResumes(files: File[], sessionId?: UUID | null): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append(files.length === 1 ? "file" : "files", file));
  if (sessionId) formData.append("session_id", sessionId);

  const endpoint = files.length === 1 ? "/upload" : "/upload-batch";
  const response = await api.post<UploadResponse>(endpoint, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function uploadResume(file: File, sessionId?: UUID | null): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (sessionId) formData.append("session_id", sessionId);

  const response = await api.post<UploadResponse>("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}
