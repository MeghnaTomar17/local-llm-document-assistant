import { api } from "./http";
import type { BulkImportStatus } from "../types";

export async function getBulkImportStatus(): Promise<BulkImportStatus> {
  const response = await api.get<BulkImportStatus>("/bulk-import/status");
  return response.data;
}

export interface ResumeUploadBatchResponse {
  uploaded_documents?: Array<Record<string, unknown>>;
  errors?: ResumeUploadError[];
  message?: string;
}

export interface ResumeUploadError {
  file_name?: string;
  error?: string;
  duplicate?: boolean;
}

export async function uploadResumes(files: File[]): Promise<ResumeUploadBatchResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const response = await api.post<ResumeUploadBatchResponse>("/upload-batch", formData);
  return response.data;
}
