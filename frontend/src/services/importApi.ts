import { api } from "./http";
import type { BulkImportStatus } from "../types";

export async function getBulkImportStatus(): Promise<BulkImportStatus> {
  const response = await api.get<BulkImportStatus>("/bulk-import/status");
  return response.data;
}
