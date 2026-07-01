import { api } from "./http";
import type { ChatMessage, UUID } from "../types";

export async function getChatHistory(sessionId: UUID, resumeId?: UUID): Promise<ChatMessage[]> {
  const response = await api.get<{ messages: ChatMessage[] }>("/chat-history", {
    params: { session_id: sessionId, resume_id: resumeId },
  });
  return response.data.messages || [];
}

export async function askResumeQuestion(question: string, sessionId: UUID, resumeId?: UUID): Promise<{
  answer: string;
  response_time?: number;
  message: ChatMessage;
}> {
  const response = await api.post("/ask", {
    question,
    session_id: sessionId,
    resume_id: resumeId,
  });
  return response.data;
}
