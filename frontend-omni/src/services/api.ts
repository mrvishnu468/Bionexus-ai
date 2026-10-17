
import type {
  DatasetEvaluation,
  DatasetSuitability,
  DatasetAssayType,
} from "../types/api";

export const API_BASE_URL = "http://127.0.0.1:8000";

export const apiRoutes = {
  health: "/health",
  datasetSearch: "/api/datasets/search",
  datasetEvaluation: "/api/evaluation/dataset",
  research: "/api/research",
  researchById: (researchId: string) => `/api/research/${researchId}`,
} as const;

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
}

export interface DatasetSearchRequest {
  query: string;
  retmax?: number;
}

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
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
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
      const body: { detail?: string } = await response.json();
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the HTTP status message when the response has no JSON detail.
    }

    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export function searchDatasets(
  request: DatasetSearchRequest,
): Promise<DatasetSearchResponse> {
  return apiRequest<DatasetSearchResponse>(apiRoutes.datasetSearch, {
    method: "POST",
    body: JSON.stringify({
      query: request.query.trim(),
      retmax: request.retmax ?? 10,
    }),
  });
}

export function evaluateDataset(
  accession: string,
): Promise<DatasetEvaluation> {
  return apiRequest<DatasetEvaluation>(apiRoutes.datasetEvaluation, {
    method: "POST",
    body: JSON.stringify({ accession }),
  });
}

export async function checkBackendHealth(): Promise<boolean> {
  const result = await apiRequest<{ status: string }>(apiRoutes.health);
  return result.status === "ok";
}

export type { DatasetEvaluation, DatasetSuitability, DatasetAssayType };
