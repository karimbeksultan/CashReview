export type Lang = "en" | "ru";
export type Page = "review" | "sources" | "system";
export type Decision = "violation" | "no_violation" | "needs_review";
export type Evidence = { timestamp_sec: number; image_base64: string };
export type Finding = {
  type: string;
  timecode_sec: number;
  description: string;
  rule_id?: string;
  confidence?: number;
  evidence_frames?: Evidence[];
};
export type HumanReview = {
  decision: Decision;
  notes: string;
  event_index: number | null;
  updated_at: number;
};
export type ReviewInput = {
  decision: Decision;
  notes: string;
  event_index?: number | null;
};
export type ReviewDraft = {
  decision: Decision | "";
  notes: string;
  scope: string;
  saved: boolean;
};
export type Job = {
  job_id: string;
  status: "processing" | "done" | "failed";
  deadline_at?: number;
  progress?: number;
  stage?: string;
  verdict?: "violation" | "no_violation";
  violations?: Finding[];
  metadata?: Record<string, unknown>;
  human_review?: HumanReview | null;
  error?: { message?: string; code?: string } | string;
  result?: Partial<Job>;
};
export type Rule = {
  id: string;
  title: string;
  issuer?: string;
  url?: string;
  section?: string;
  summary?: string;
  applicability?: string;
  limitations?: string | string[];
  enabled_for_legal_claim?: boolean;
};
export type Health = {
  ready?: boolean;
  reasons?: string[];
  model_kind?: string;
  model_version?: string;
  max_upload_bytes?: number;
  validation_status?: string;
  limitations?: string[];
  validation_summary?: Record<string, unknown>;
  engine?: Health;
};
export type FrameSelection = { event: number; frame: number };
