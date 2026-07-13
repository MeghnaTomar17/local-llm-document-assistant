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
  interview_marked?: boolean;
  candidate_type?: "INTERNAL" | "EXTERNAL";
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
  interview_marked?: boolean | null;
  candidate_type?: "INTERNAL" | "EXTERNAL" | null;
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
  interview_marked?: boolean | null;
  candidate_type?: "INTERNAL" | "EXTERNAL" | null;
  search_score?: number | null;
  match_explanation?: string[] | null;
  match_details?: Record<string, unknown> | null;
  normalized_candidate_skills?: string[] | null;
  matched_skills?: string[] | null;
  missing_skills?: string[] | null;
  [key: string]: unknown;
}

export interface SearchResponse {
  question: string;
  generated_sql?: string | null;
  row_count: number;
  execution_time_ms?: number | null;
  results: SearchResult[];
  model_used?: string | null;
  requirement_analysis?: Record<string, unknown>;
  debug_report_path?: string | null;
  relaxation_attempts?: Array<Record<string, unknown>>;
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
  state?: "IDLE" | "RUNNING" | "COMPLETED" | "INTERRUPTED";
  running: boolean;
  processed: number;
  total: number;
  failed: number;
  duplicates?: number;
  duplicate_warnings?: Array<{
    file_name: string;
    candidate_name: string;
    email: string;
    phone: string;
    reason: string;
    timestamp: string;
  }>;
  current_file?: string | null;
  last_completed_file?: string | null;
  message?: string | null;
  started_at?: string | null;
  updated_at?: string | null;
  finished_at?: string | null;
  interrupted?: boolean;
  interrupted_at?: string | null;
  pid?: number | null;
}
