export interface SelectedResearchDataset {
  accession: string;
  studyAccession: string | null;
  title: string;
  organism: string | null;
  assayType: string;
  suitability: string;
  researchQuery: string;
  selectedAt: string;
}

export interface ResearchContext {
  researchQuery: string;
  selectedDataset: SelectedResearchDataset | null;
}

const STORAGE_KEY = "bionexus-research-context-v1";

export function readResearchContext(): ResearchContext | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object") return null;

    const context = value as Partial<ResearchContext>;
    if (typeof context.researchQuery !== "string") return null;

    return {
      researchQuery: context.researchQuery,
      selectedDataset: context.selectedDataset ?? null,
    };
  } catch {
    return null;
  }
}

export function saveResearchContext(context: ResearchContext): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(context));
}