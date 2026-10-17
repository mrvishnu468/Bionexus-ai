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
