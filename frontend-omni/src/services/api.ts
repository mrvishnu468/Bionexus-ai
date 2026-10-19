
import type {
  DatasetEvaluation,
  DatasetSuitability,
  DatasetAssayType,
  ResearchIntent,
  IntentInterpretationResponse,
  IntentApprovalResponse,
} from "../types/api";

export const API_BASE_URL = "http://127.0.0.1:8000";

export const apiRoutes = {
  health: "/health",
  intentInterpret: "/api/intent/interpret",
  intentApprove: "/api/intent/approve",
  datasetSearch: "/api/datasets/search",
  datasetEvaluation: "/api/evaluation/dataset",
  research: "/api/research",
  researchById: (researchId: string) => `/api/research/${researchId}`,
} as const;

export const geoApiRoutes = {
  validate: "/api/geo/validate",
  prepareAnalysis: "/api/geo/prepare-analysis",
  executeAnalysis: "/api/geo/execute-analysis",
} as const;

// -----------------------------------------------------------------------------
// SRA dataset interfaces
// -----------------------------------------------------------------------------

export interface SRARun {
  accession: string;
  experiment_accession?: string | null;
  sample_accession?: string | null;
}

export interface SRASample {
  accession: string;
  title?: string | null;
  organism?: string | null;
  attributes: Record<string, string>;
  experiment_accession?: string | null;
  study_accession?: string | null;
  runs: SRARun[];
}

export interface SRAExperiment {
  accession: string;
  title?: string | null;
  study_accession?: string | null;
  organism?: string | null;
  samples: SRASample[];
}

export interface SRADataset {
  accession: string;
  study_accession?: string | null;
  title?: string | null;
  organism?: string | null;
  library_strategy?: string | null;
  library_source?: string | null;
  description?: string | null;
  sample_count?: number | null;
  run_count?: number | null;
  study_title?: string | null;
  study_abstract?: string | null;
  experiment_type?: string | null;
  experiments: SRAExperiment[];
  samples: SRASample[];
}

export interface DatasetSearchResult {
  dataset: SRADataset;
  evaluation: DatasetEvaluation;
}

export interface DatasetSearchResponse {
  datasets: DatasetSearchResult[];
  review_required?: boolean;
  ready_for_ranking?: boolean;
  clarification_questions?: string[];
  review_reasons?: string[];
}

export interface DatasetSearchRequest {
  query: string;
  retmax?: number;
  intent?: ResearchIntent;
  approval_token?: string;
}

export interface IntentInterpretationRequest {
  query: string;
}

export interface IntentApprovalRequest {
  intent: ResearchIntent;
}

// -----------------------------------------------------------------------------
// GEO analysis interfaces
// -----------------------------------------------------------------------------

export interface GeoSampleAssignment {
  sample_accession: string;
  group: string;
}

export interface GeoDesignAssignment {
  sample_accession: string;
  suggested_group: string | null;
  group_evidence: string[];
  confirmed_group: string | null;
}

export interface GeoPreparedAnalysis {
  accession: string;
  title: string;
  source_url: string;
  provenance: {
    sha256: string;
    cache_hit: boolean;
    accessed_at?: string | null;
    retrieved_at?: string | null;
  };
  matrix_validation: {
    status: string;
    ready_for_design_review: boolean;
    assay_type: string;
    data_representation: string;
    matrix_rows: number;
    matrix_columns: number;
    errors: string[];
    warnings: string[];
    [key: string]: unknown;
  };
  expression: Record<string, unknown>;
  sample_manifest: {
    samples?: Array<Record<string, unknown>>;
    pairing_candidates?: Array<Record<string, unknown>>;
    warnings?: string[];
    [key: string]: unknown;
  };
  design_review: {
    status: string;
    approved: boolean;
    group_assignments: GeoDesignAssignment[];
    suggested_groups: Array<{
      name: string;
      sample_accessions: string[];
    }>;
    pairing_candidates: Array<Record<string, unknown>>;
    pairing_approved: boolean;
    warnings: string[];
  };
  analysis_status: string;
  analysis_executed: boolean;
}

export interface GeoDifferentialExpressionRow {
  gene_id: string;
  direction: string;
  contrast: string;
  log2_fold_change: number;
  average_expression: number;
  moderated_t: number;
  p_value: number;
  adjusted_p_value: number;
  B_statistic: number;
}

export interface GeoLimmaResult {
  engine: string;
  contrast: string;
  features_tested: number;
  significance_threshold: number;
  results: GeoDifferentialExpressionRow[];
  stdout?: string;
}

export interface GeoExecutionResponse {
  accession: string;
  title: string;
  analysis_status: string;
  analysis_method: string;
  assay_type: string;
  comparison: {
    numerator_group: string;
    denominator_group: string;
    direction_explanation?: string;
  };
  sample_count: number;
  matrix_sha256: string;
  source_url: string;
  cache_hit: boolean;
  retrieved_at?: string | null;
  result_count: number;
  results: GeoLimmaResult;
}

export interface GeoValidationResponse {
  accession: string;
  title: string;
  status: string;
  ready_for_design_review: boolean;
  assay_type: string;
  data_representation: string;
  platform_ids: string[];
  matrix_rows: number;
  matrix_columns: number;
  metadata_sample_count: number;
  sample_ids_aligned: boolean;
  errors: string[];
  warnings: string[];
  [key: string]: unknown;
}

/**
 * A researcher-reviewed candidate pair for paired differential-expression
 * analysis. The backend must independently verify the GEO sample evidence.
 */
export interface GeoApprovedPair {
  tumour_accession: string;
  normal_accession: string;
  patient_id: string;
  approved: boolean;
}

export interface GeoExecuteAnalysisRequest {
  accession: string;
  assignments: GeoSampleAssignment[];
  numerator_group: string;
  denominator_group: string;
  assay_type: "processed_microarray";
  normalization_confirmed: boolean;
  design_confirmed: boolean;
  paired_analysis?: boolean;
  approved_pairs?: GeoApprovedPair[];
}

// -----------------------------------------------------------------------------
// Shared HTTP helpers
// -----------------------------------------------------------------------------

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(apiUrl(path), {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body
          ? { "Content-Type": "application/json" }
          : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new Error(
      `Cannot connect to the BioNexus backend at ${API_BASE_URL}. Check that the backend is running.`,
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;

    try {
      const body: { detail?: unknown } = await response.json();

      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail !== undefined) {
        detail = JSON.stringify(body.detail);
      }
    } catch {
      // Keep the HTTP status message when the response has no JSON detail.
    }

    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

// -----------------------------------------------------------------------------
// Research intent
// -----------------------------------------------------------------------------

export function interpretResearchIntent(
  request: IntentInterpretationRequest,
): Promise<IntentInterpretationResponse> {
  return apiRequest<IntentInterpretationResponse>(
    apiRoutes.intentInterpret,
    {
      method: "POST",
      body: JSON.stringify({
        query: request.query.trim(),
      }),
    },
  );
}

export function approveResearchIntent(
  request: IntentApprovalRequest,
): Promise<IntentApprovalResponse> {
  return apiRequest<IntentApprovalResponse>(
    apiRoutes.intentApprove,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

// -----------------------------------------------------------------------------
// Dataset discovery and evaluation
// -----------------------------------------------------------------------------

export function searchDatasets(
  request: DatasetSearchRequest,
): Promise<DatasetSearchResponse> {
  return apiRequest<DatasetSearchResponse>(
    apiRoutes.datasetSearch,
    {
      method: "POST",
      body: JSON.stringify({
        query: request.query.trim(),
        retmax: request.retmax ?? 10,
        ...(request.intent ? { intent: request.intent } : {}),
        ...(request.approval_token
          ? { approval_token: request.approval_token }
          : {}),
      }),
    },
  );
}

export function evaluateDataset(
  accession: string,
): Promise<DatasetEvaluation> {
  return apiRequest<DatasetEvaluation>(
    apiRoutes.datasetEvaluation,
    {
      method: "POST",
      body: JSON.stringify({ accession }),
    },
  );
}

// -----------------------------------------------------------------------------
// Backend health
// -----------------------------------------------------------------------------

export async function checkBackendHealth(): Promise<boolean> {
  const result = await apiRequest<{ status: string }>(
    apiRoutes.health,
  );

  return result.status === "ok";
}

// -----------------------------------------------------------------------------
// GEO matrix validation
// -----------------------------------------------------------------------------

export function validateGeoMatrix(
  accession: string,
): Promise<GeoValidationResponse> {
  return apiRequest<GeoValidationResponse>(
    geoApiRoutes.validate,
    {
      method: "POST",
      body: JSON.stringify({
        accession: accession.trim(),
      }),
    },
  );
}

// -----------------------------------------------------------------------------
// GEO analysis preparation and sample-group review
// -----------------------------------------------------------------------------

export function prepareGeoAnalysis(
  accession: string,
): Promise<GeoPreparedAnalysis> {
  return apiRequest<GeoPreparedAnalysis>(
    geoApiRoutes.prepareAnalysis,
    {
      method: "POST",
      body: JSON.stringify({
        accession: accession.trim(),
      }),
    },
  );
}

// -----------------------------------------------------------------------------
// GEO limma differential-expression execution
// -----------------------------------------------------------------------------

export function executeGeoAnalysis(
  request: GeoExecuteAnalysisRequest,
): Promise<GeoExecutionResponse> {
  return apiRequest<GeoExecutionResponse>(
    geoApiRoutes.executeAnalysis,
    {
      method: "POST",
      body: JSON.stringify({
        ...request,
        accession: request.accession.trim(),
      }),
    },
  );
}

// -----------------------------------------------------------------------------
// Publicly re-export shared API types
// -----------------------------------------------------------------------------

export type {
  DatasetEvaluation,
  DatasetSuitability,
  DatasetAssayType,
  ResearchIntent,
  IntentInterpretationResponse,
  IntentApprovalResponse,
};
