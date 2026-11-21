export type ExtractionMethod =
  | "company_list_exact"
  | "company_list_fuzzy"
  | "deterministic_rules"
  | "llm_fallback"
  | "needs_review";

export interface HealthResponse {
  status: "ok";
  ocr_engine: string;
  llm_provider: string;
  llm_configured: boolean;
}

export interface AnalyzeDocumentResponse {
  original_filename: string;
  extension: string;
  sha256: string;
  size_bytes: number;
  page_count: number;
  ocr_source: "pdf_text" | "rapidocr" | "hybrid";
  suggested_name: string | null;
  safe_filename: string | null;
  confidence: number;
  method: ExtractionMethod;
  ambiguous: boolean;
  evidence: string | null;
  ocr_excerpt: string;
  llm_used: boolean;
  llm_reasoning: string | null;
  latency_ms: number;
}

export interface CompanyListResponse {
  count: number;
  companies: string[];
  source_filename: string;
}

export interface DocumentItem {
  id: string;
  file: File;
  previewUrl: string | null;
  status: "analyzing" | "ready" | "error";
  error?: string;
  analysis?: AnalyzeDocumentResponse;
  editedName: string;
  approved: boolean;
  isDuplicate: boolean;
}
