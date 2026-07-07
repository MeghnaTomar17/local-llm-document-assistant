import { api } from "./http";
import type { ResumeListItem, SessionsResponse, UUID } from "../types";

export async function listSessions(): Promise<SessionsResponse> {
  const response = await api.get<SessionsResponse>("/sessions");
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
