import { useEffect, useState, type FormEvent } from "react";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import {
  searchDatasets,
  type DatasetSearchResult,
} from "../services/api";
const DATASET_DISCOVERY_STORAGE_KEY = "bionexus-dataset-discovery-v1";

interface SavedDatasetDiscovery {
  query: string;
  results: DatasetSearchResult[];
  hasSearched: boolean;
}

function loadDatasetDiscovery(): SavedDatasetDiscovery {
  const fallback: SavedDatasetDiscovery = {
    query: "",
    results: [],
    hasSearched: false,
  };

  try {
    const saved = localStorage.getItem(DATASET_DISCOVERY_STORAGE_KEY);
    if (!saved) return fallback;

    const parsed: unknown = JSON.parse(saved);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !("query" in parsed) ||
      typeof parsed.query !== "string" ||
      !("results" in parsed) ||
      !Array.isArray(parsed.results) ||
      !("hasSearched" in parsed) ||
      typeof parsed.hasSearched !== "boolean"
    ) {
      return fallback;
    }

    return {
      query: parsed.query,
      results: parsed.results as DatasetSearchResult[],
      hasSearched: parsed.hasSearched,
    };
  } catch {
    return fallback;
  }
}
export function DatasetDiscoveryPage() {
  const [initialState] = useState(loadDatasetDiscovery);
const [query, setQuery] = useState(initialState.query);
const [results, setResults] = useState<DatasetSearchResult[]>(
  initialState.results,
);
const [loading, setLoading] = useState(false);
const [error, setError] = useState("");
const [hasSearched, setHasSearched] = useState(initialState.hasSearched);

useEffect(() => {
  try {
    localStorage.setItem(
      DATASET_DISCOVERY_STORAGE_KEY,
      JSON.stringify({ query, results, hasSearched }),
    );
  } catch (err) {
    console.warn("Could not save dataset discovery state.", err);
  }
}, [query, results, hasSearched]);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery || loading) return;

    setLoading(true);
    setError("");
    setHasSearched(true);

    try {
      const response = await searchDatasets({
        query: trimmedQuery,
        retmax: 10,
      });
      setResults(response.datasets);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Dataset search failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        kicker="DATA DISCOVERY"
        title="Find research datasets"
        description="Discover public NCBI/SRA studies and evaluate their suitability before selecting a dataset for analysis."
      />

      <form className="workspace-form" onSubmit={handleSearch}>
        <label htmlFor="dataset-query">Research query</label>

        <div className="form-row">
          <input
            id="dataset-query"
            type="search"
            placeholder="e.g. diabetes Homo sapiens RNA-Seq"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            disabled={loading}
            required
          />

          <Button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Searching..." : "Search SRA"}
          </Button>
        </div>

        <p className="form-note">
          Search the live BioNexus backend. Results include available study
          metadata and suitability evaluations from the current evaluator.
        </p>
      </form>

      {loading && (
        <EmptyState title="Searching NCBI/SRA">
          Retrieving matching datasets and evaluating their suitability.
          Results will appear here when the search finishes.
        </EmptyState>
      )}

      {!loading && error && (
        <EmptyState title="Dataset search failed">
          <p>{error}</p>
          <p>Check that the BioNexus backend is running, then try again.</p>
        </EmptyState>
      )}

      {!loading && !error && hasSearched && results.length === 0 && (
        <EmptyState title="No datasets found">
          Try a broader disease name, organism, or sequencing term.
        </EmptyState>
      )}

      {!loading && !error && results.length > 0 && (
        <section className="dataset-results" aria-live="polite">
          <div className="dataset-results-heading">
            <div>
              <p className="eyebrow">DISCOVERY RESULTS</p>
              <h2>Matching datasets</h2>
              <p className="form-note">
                Review each dataset's metadata and suitability before choosing
                it for a research workflow.
              </p>
            </div>

            <span className="dataset-accession">
              {results.length} result{results.length === 1 ? "" : "s"}
            </span>
          </div>

          {results.map(({ dataset, evaluation }) => {
            const title =
              dataset.study_title ||
              dataset.title ||
              dataset.accession;

            return (
              <article
                className="dataset-result-card"
                key={`${dataset.accession}-${evaluation.accession}`}
              >
                <div className="dataset-card-top">
                  <div className="dataset-card-title">
                    <p className="eyebrow">RESEARCH STUDY</p>
                    <h3>{title}</h3>

                    <div className="dataset-accession">
                      Study: {dataset.study_accession || "Not reported"}
                      <span aria-hidden="true"> · </span>
                      Dataset: {dataset.accession}
                    </div>
                  </div>

                  <span
                    className={`dataset-status dataset-status-${evaluation.suitability}`}
                  >
                    {evaluation.suitability.replaceAll("_", " ")}
                  </span>
                </div>

                {dataset.title &&
                  dataset.study_title &&
                  dataset.title !== dataset.study_title && (
                    <p className="dataset-abstract">
                      {dataset.title}
                    </p>
                  )}

                {(dataset.study_abstract || dataset.description) && (
                  <p className="dataset-abstract">
                    {dataset.study_abstract || dataset.description}
                  </p>
                )}

                <div className="dataset-metrics">
                  <div className="dataset-metric">
                    <span>Suitability score</span>
                    <strong>{evaluation.score}</strong>
                  </div>

                  <div className="dataset-metric">
                    <span>Organism</span>
                    <strong>{dataset.organism || "Not reported"}</strong>
                  </div>

                  <div className="dataset-metric">
                    <span>Samples</span>
                    <strong>{dataset.sample_count ?? "Not reported"}</strong>
                  </div>

                  <div className="dataset-metric">
                    <span>Runs</span>
                    <strong>{dataset.run_count ?? "Not reported"}</strong>
                  </div>
                </div>

                <div className="dataset-card-section">
                  <h4>Dataset metadata</h4>

                  <div className="dataset-metadata">
                    <div className="dataset-metadata-item">
                      <span>Assay type</span>
                      <strong>
                        {evaluation.assay_type.replaceAll("_", " ")}
                      </strong>
                    </div>

                    <div className="dataset-metadata-item">
                      <span>Library strategy</span>
                      <strong>
                        {dataset.library_strategy || "Not reported"}
                      </strong>
                    </div>

                    <div className="dataset-metadata-item">
                      <span>Library source</span>
                      <strong>
                        {dataset.library_source || "Not reported"}
                      </strong>
                    </div>

                    <div className="dataset-metadata-item">
                      <span>Experiment type</span>
                      <strong>
                        {dataset.experiment_type || "Not reported"}
                      </strong>
                    </div>
                  </div>
                </div>

                {evaluation.reasons.length > 0 && (
                  <div className="dataset-card-section">
                    <h4>Suitability assessment</h4>
                    <ul className="dataset-evaluation-list">
                      {evaluation.reasons.map((reason, index) => (
                        <li key={`${index}-${reason}`}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {evaluation.warnings.length > 0 && (
                  <div className="dataset-card-section">
                    <h4>Review before using</h4>
                    <ul className="dataset-warning-list">
                      {evaluation.warnings.map((warning, index) => (
                        <li key={`${index}-${warning}`}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {dataset.experiments.length > 0 && (
                  <details className="dataset-hierarchy">
                    <summary>
                      Explore experiment hierarchy
                      <span>
                        {dataset.experiments.length} experiment
                        {dataset.experiments.length === 1 ? "" : "s"}
                      </span>
                    </summary>

                    <div className="dataset-hierarchy-content">
                      {dataset.experiments.map((experiment) => (
                        <div
                          className="dataset-experiment"
                          key={experiment.accession}
                        >
                          <h4>{experiment.accession}</h4>

                          {experiment.title && (
                            <p>{experiment.title}</p>
                          )}

                          {experiment.organism && (
                            <p>
                              <strong>Organism:</strong>{" "}
                              {experiment.organism}
                            </p>
                          )}

                          {experiment.samples.length > 0 ? (
                            experiment.samples.map((sample) => (
                              <div
                                className="dataset-sample"
                                key={sample.accession}
                              >
                                <p>
                                  <strong>Sample:</strong>{" "}
                                  {sample.accession}
                                </p>

                                {sample.title && <p>{sample.title}</p>}

                                {sample.runs.length > 0 && (
                                  <p>
                                    <strong>Runs:</strong>{" "}
                                    {sample.runs
                                      .map((run) => run.accession)
                                      .join(", ")}
                                  </p>
                                )}
                              </div>
                            ))
                          ) : (
                            <p className="form-note">
                              No sample details are available for this
                              experiment.
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </article>
            );
          })}
        </section>
      )}

      {!loading && !error && !hasSearched && (
        <EmptyState title="Ready to discover datasets">
          Enter a disease, organism, or sequencing query to find public
          research datasets. Search results will appear here when retrieved.
        </EmptyState>
      )}
    </div>
  );
}
