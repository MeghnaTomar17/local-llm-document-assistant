import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg || JSON.stringify(item)).join("\n");
    if (!error.response) return "Unable to reach the server. Please check that the backend is running.";
    if (error.response.status >= 500) return "Something went wrong on the server. Please try again.";
    return "Request failed. Please try again.";
  }
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}
