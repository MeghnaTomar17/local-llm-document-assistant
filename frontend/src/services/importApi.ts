import { api } from "./http";
import type { BulkImportStatus } from "../types";

export async function getBulkImportStatus(): Promise<BulkImportStatus> {
  const response = await api.get<BulkImportStatus>("/bulk-import/status");
  return response.data;
}

export interface ResumeUploadBatchResponse {
  uploaded_documents?: Array<Record<string, unknown>>;
  errors?: Array<Record<string, unknown>>;
  message?: string;
}

export async function uploadResumes(files: File[]): Promise<ResumeUploadBatchResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const response = await api.post<ResumeUploadBatchResponse>("/upload-batch", formData);
  return response.data;
}
