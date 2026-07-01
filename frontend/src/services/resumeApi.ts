import { api } from "./http";
import type { ResumeDetail, ResumeListResponse, ResumeUpdate, UUID } from "../types";

export async function listResumes(): Promise<ResumeListResponse> {
  const response = await api.get<ResumeListResponse>("/resumes");
  return response.data;
}

export async function getResume(id: UUID): Promise<ResumeDetail> {
  const response = await api.get<ResumeDetail>(`/resumes/${id}`);
  return response.data;
}

export async function updateResume(id: UUID, payload: ResumeUpdate): Promise<ResumeDetail> {
  const response = await api.put<ResumeDetail>(`/resumes/${id}`, payload);
  return response.data;
}

export async function deleteResume(id: UUID): Promise<void> {
  await api.delete(`/resumes/${id}`);
}

export function getResumeDownloadUrl(id: UUID): string {
  const baseURL = api.defaults.baseURL || "";
  return `${baseURL}/resumes/${id}/download`;
}

export function getResumePreviewUrl(id: UUID): string {
  const baseURL = api.defaults.baseURL || "";
  return `${baseURL}/resumes/${id}/preview`;
}
