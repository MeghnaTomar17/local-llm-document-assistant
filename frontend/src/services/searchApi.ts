import { api } from "./http";
import type { SearchHistoryItem, SearchResponse, UUID } from "../types";

export async function recruiterSearch(
  query: string,
  sessionId?: UUID | null,
  candidateType?: string | null,
  signal?: AbortSignal
): Promise<SearchResponse> {
  const response = await api.post<SearchResponse>("/search", {
    query,
    session_id: sessionId || undefined,
    candidate_type: candidateType || undefined,
  }, { signal });
  return response.data;
}

export async function listSearchHistory(sessionId?: UUID | null): Promise<SearchHistoryItem[]> {
  const response = await api.get<SearchHistoryItem[]>(
    sessionId ? `/search-history/${sessionId}` : "/search-history",
  );
  return response.data;
}

export async function getSearchHistoryItem(id: UUID): Promise<SearchHistoryItem> {
  const response = await api.get<SearchHistoryItem>(`/search-history/item/${id}`);
  return response.data;
}

export async function deleteSearchHistoryItem(id: UUID): Promise<void> {
  await api.delete(`/search-history/${id}`);
}

export async function clearSearchHistory(sessionId?: UUID | null): Promise<{ deleted: number }> {
  const response = await api.delete(sessionId ? `/search-history/session/${sessionId}` : "/search-history");
  return response.data;
}
