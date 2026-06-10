import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function askQuestion(question, sessionId) {
  const response = await api.post("/ask", { question, session_id: sessionId });
  return response.data;
}

export async function getStats(sessionId) {
  const response = await api.get("/stats", { params: sessionId ? { session_id: sessionId } : {} });
  return response.data;
}

export async function getChatHistory(sessionId) {
  const response = await api.get("/chat-history", { params: sessionId ? { session_id: sessionId } : {} });
  return response.data.messages;
}

export async function clearChat(sessionId) {
  const response = await api.post("/clear-chat", sessionId ? { session_id: sessionId } : {});
  return response.data.messages;
}

export async function getSessions() {
  const response = await api.get("/sessions");
  return response.data;
}

export async function switchSession(sessionId) {
  const response = await api.post("/switch-session", { session_id: sessionId });
  return response.data;
}

export async function getDebugData(sessionId) {
  const response = await api.get("/debug", { params: sessionId ? { session_id: sessionId } : {} });
  return response.data;
}
