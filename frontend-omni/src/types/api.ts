/**
 * Shared frontend contracts aligned with the existing BioNexus API.
 * These types are reserved for later milestones. No client calls them yet.
 */

export type DatasetSuitability =
  | "recommended"
  | "conditional"
  | "not_recommended";

export type DatasetAssayType =
  | "bulk_rna_seq"
  | "single_cell_rna_seq"
  | "single_nucleus_rna_seq"
  | "other"
  | "unknown";

export type ResearchStatus =
  | "queued"
  | "planning"
  | "dataset_discovery"
  | "dataset_evaluation"
  | "analysis"
  | "pathways"
  | "literature"
  | "scientific_review"
  | "report"
  | "completed"
  | "failed";

export interface ResearchJob {
  research_id: string;
  question: string;
  status: ResearchStatus;
  message: string;
}

export interface DatasetEvaluation {
  accession: string;
  suitability: DatasetSuitability;
  assay_type: DatasetAssayType;
  score: number;
  reasons: string[];
  warnings: string[];
}
export type IntentFieldStatus =
  | "explicit"
  | "inferred"
  | "confirmed"
  | "unknown"
  | "ambiguous";

export type IntentReviewStatus =
  | "proposed"
  | "needs_clarification"
  | "confirmed";

export interface IntentField {
  value: string | null;
  status: IntentFieldStatus;
  evidence: string[];
}

export interface ResearchIntent {
  original_question: string;
  review_status: IntentReviewStatus;
  research_goal: IntentField;
  disease: IntentField;
  gene: IntentField;
  organism: IntentField;
  tissue: IntentField;
  assay_type: IntentField;
  analysis_goal: IntentField;
  comparison: IntentField;
  constraints: string[];
  clarification_required: boolean;
  clarification_questions: string[];
}

export interface IntentInterpretationResponse {
  intent: ResearchIntent;
  source: "ai" | "rules_fallback";
  warning?: string | null;
}

export interface IntentApprovalResponse {
  intent: ResearchIntent;
  approval_token: string;
  expires_in_seconds: number;
}