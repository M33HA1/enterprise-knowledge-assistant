export type UserRole = "employee" | "admin" | "super_admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department_id?: string | null;
  department_name?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SourceCitation {
  document: string;
  page: string | number;
  department: string;
  relevance_score: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceCitation[];
  confidence: number;
  needs_escalation: boolean;
  model_used: string;
  tokens_used: number;
  chunks_retrieved: number;
  response_time_ms: number;
  query_id: string;
}

export interface QueryHistoryItem {
  id: string;
  question: string;
  answer: string;
  confidence: number | null;
  needs_escalation: boolean;
  sources: string | null;
  model_used: string | null;
  response_time_ms: number | null;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  filename: string;
  file_type: string;
  status: string;
  chunk_count: number;
  department_name?: string | null;
  created_at: string;
}

export interface Department {
  id: string;
  name: string;
  description?: string | null;
}
