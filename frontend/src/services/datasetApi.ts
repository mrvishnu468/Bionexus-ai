const API_BASE_URL = "http://127.0.0.1:8000";

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

export interface SRARun {
  accession: string;
  experiment_accession: string | null;
  sample_accession: string | null;
}

export interface SRASample {
  accession: string;
  title: string | null;
  organism: string | null;
  attributes: Record<string, string>;
  experiment_accession: string | null;
  study_accession: string | null;
  runs: SRARun[];
}

export interface SRAExperiment {
  accession: string;
  title: string | null;
  study_accession: string | null;
  samples: SRASample[];
}

export interface SRADataset {
  accession: string;
  study_accession: string | null;
  title: string | null;
  organism: string | null;
  library_strategy: string | null;
  library_source: string | null;
  description: string | null;
  sample_count: number | null;
  run_count: number | null;
  study_title: string | null;
  study_abstract: string | null;
  experiment_type: string | null;
  experiments: SRAExperiment[];
  samples: SRASample[];
}

export interface DatasetEvaluation {
  accession: string;
  suitability: DatasetSuitability;
  assay_type: DatasetAssayType;
  score: number;
  reasons: string[];
  warnings: string[];
}

export interface DatasetSearchResult {
  dataset: SRADataset;
  evaluation: DatasetEvaluation;
}

export interface DatasetSearchResponse {
  datasets: DatasetSearchResult[];
}

export async function searchDatasets(
  query: string,
  retmax: number = 10,
): Promise<DatasetSearchResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/datasets/search`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        retmax,
      }),
    },
  );

  if (!response.ok) {
    throw new Error("Failed to search datasets.");
  }

  return response.json();
}