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
  return response.data.document;
}

export async function askQuestion(question) {
  const response = await api.post("/ask", { question });
  return response.data;
}

export async function getStats() {
  const response = await api.get("/stats");
  return response.data;
}

export async function getChatHistory() {
  const response = await api.get("/chat-history");
  return response.data.messages;
}

export async function clearChat() {
  const response = await api.post("/clear-chat");
  return response.data.messages;
}
