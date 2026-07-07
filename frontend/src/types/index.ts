export type UUID = string;
export type HRDecision = "PENDING" | "ON_HOLD" | "ACCEPTED" | "REJECTED";

export interface ResumeListItem {
  id: UUID;
  candidate_name?: string | null;
  email?: string | null;
  phone_number?: string | null;
  skills?: string[] | null;
  cities?: string[] | null;
  fresher?: boolean | null;
  is_verified?: boolean | null;
  processing_status?: string | null;
  extraction_status?: string | null;
  original_file_name?: string | null;
  mime_type?: string | null;
  uploaded_at?: string | null;
  updated_at?: string | null;
  session_id?: UUID | null;
  hr_decision?: HRDecision | null;
  decision_at?: string | null;
}

export interface ResumeDetail extends ResumeListItem {
  notes?: string | null;
  hr_notes?: string | null;
  technical_notes?: string | null;
  final_notes?: string | null;
  stored_file_name?: string | null;
}

export interface ResumeListResponse {
  total: number;
  resumes: ResumeListItem[];
}

export interface ResumeUpdate {
  candidate_name?: string | null;
  email?: string | null;
  phone_number?: string | null;
  skills?: string[];
  cities?: string[];
  fresher?: boolean | null;
  hr_notes?: string | null;
  technical_notes?: string | null;
  final_notes?: string | null;
  hr_decision?: HRDecision | null;
}

export interface RecruiterSession {
  id?: UUID;
  session_id: UUID;
  title?: string | null;
  display_name?: string | null;
  document_count?: number;
  message_count?: number;
  is_active?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  last_active_at?: string | null;
  resume_id?: UUID | null;
  hr_decision?: HRDecision | null;
  decision_at?: string | null;
  candidate_name?: string | null;
  original_file_name?: string | null;
  uploaded_at?: string | null;
  document?: {
    name?: string;
    resume_id?: UUID;
  };
}

export interface SessionsResponse {
  active_session_id?: UUID | null;
  sessions: RecruiterSession[];
}

export interface SearchResult {
  id?: UUID;
  resume_id?: UUID;
  candidate_name?: string | null;
  email?: string | null;
  phone_number?: string | null;
  skills?: string[] | string | null;
  cities?: string[] | string | null;
  fresher?: boolean | null;
  is_verified?: boolean | null;
  hr_decision?: HRDecision | string | null;
  decision_at?: string | null;
  hr_notes?: string | null;
  technical_notes?: string | null;
  final_notes?: string | null;
  uploaded_at?: string | null;
  [key: string]: unknown;
}

export interface SearchResponse {
  question: string;
  generated_sql?: string | null;
  row_count: number;
  execution_time_ms?: number | null;
  results: SearchResult[];
}

export interface SearchHistoryItem {
  id: UUID;
  session_id: UUID;
  query: string;
  generated_sql: string;
  result_count: number;
  results_snapshot: SearchResult[];
  execution_time_ms?: number | null;
  model_used: string;
  created_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  response_time?: number;
  retrieval?: {
    chunk_count?: number;
    context_size?: number;
    strategy?: string;
    chunks?: Array<Record<string, unknown>>;
  };
  prompt_size?: number;
}

export interface BulkImportStatus {
  running: boolean;
  processed: number;
  total: number;
  failed: number;
  current_file?: string | null;
  last_completed_file?: string | null;
  message?: string | null;
  started_at?: string | null;
  updated_at?: string | null;
  finished_at?: string | null;
}
