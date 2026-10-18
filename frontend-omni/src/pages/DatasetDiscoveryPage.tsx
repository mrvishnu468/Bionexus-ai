
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import {
  approveResearchIntent,
  interpretResearchIntent,
  searchDatasets,
  type DatasetSearchResult,
} from "../services/api";
import type {
  IntentField,
  IntentInterpretationResponse,
  ResearchIntent,
} from "../types/api";

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

const intentFields: {
  key: keyof Pick<
    ResearchIntent,
    | "research_goal"
    | "disease"
    | "gene"
    | "organism"
    | "tissue"
    | "assay_type"
    | "analysis_goal"
    | "comparison"
  >;
  label: string;
}[] = [
  { key: "research_goal", label: "Research goal" },
  { key: "disease", label: "Disease" },
  { key: "gene", label: "Gene" },
  { key: "organism", label: "Organism" },
  { key: "tissue", label: "Tissue or sample" },
  { key: "assay_type", label: "Assay type" },
  { key: "analysis_goal", label: "Analysis goal" },
  { key: "comparison", label: "Comparison" },
];

function displayField(field: IntentField): string {
  return field.value?.trim() || "Not specified";
}

function formatStatus(status: string): string {
  return status.replaceAll("_", " ");
}

export function DatasetDiscoveryPage() {
  const [initialState] = useState(loadDatasetDiscovery);
  const [query, setQuery] = useState(initialState.query);
  const [results, setResults] = useState<DatasetSearchResult[]>(
    initialState.results,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(
    initialState.hasSearched,
  );

  const [interpretation, setInterpretation] =
    useState<IntentInterpretationResponse | null>(null);
  const [confirmedForApproval, setConfirmedForApproval] = useState(false);
  const [reviewMessage, setReviewMessage] = useState("");
  const [reviewQuestions, setReviewQuestions] = useState<string[]>([]);
  const [reviewReasons, setReviewReasons] = useState<string[]>([]);

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

  function resetReview() {
    setInterpretation(null);
    setConfirmedForApproval(false);
    setReviewMessage("");
    setReviewQuestions([]);
    setReviewReasons([]);
    setError("");
    setResults([]);
    setHasSearched(false);
  }

  async function handleInterpret(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery || loading) return;

    setLoading(true);
    resetReview();

    try {
      const response = await interpretResearchIntent({
        query: trimmedQuery,
      });

      setInterpretation(response);

      if (response.warning) {
        setReviewMessage(response.warning);
      }

      if (response.intent.clarification_questions.length > 0) {
        setReviewQuestions(response.intent.clarification_questions);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not interpret the research query. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleApproveAndSearch() {
    if (!interpretation || loading || !confirmedForApproval) return;

    setLoading(true);
    setError("");
    setReviewMessage("");
    setReviewQuestions([]);
    setReviewReasons([]);
    setResults([]);
    setHasSearched(false);

    try {
      const approved = await approveResearchIntent({
        intent: interpretation.intent,
      });

      // Keep the short-lived approval token in memory only.
      const response = await searchDatasets({
        query: query.trim(),
        retmax: 10,
        intent: approved.intent,
        approval_token: approved.approval_token,
      });

      setHasSearched(true);
      setResults(response.datasets);

      if (response.review_required || response.ready_for_ranking === false) {
        setReviewMessage(
          "The backend requires further review before these datasets can be ranked.",
        );
      }

      setReviewQuestions(response.clarification_questions ?? []);
      setReviewReasons(response.review_reasons ?? []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Approval or dataset search failed. Please review the criteria and try again.",
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
        description="Interpret your research question, review the proposed criteria, and approve them before discovering public NCBI/SRA datasets."
      />

      <form className="workspace-form" onSubmit={handleInterpret}>
        <label htmlFor="dataset-query">Research query</label>

        <div className="form-row">
          <input
            id="dataset-query"
            type="search"
            placeholder="e.g. diabetes Homo sapiens RNA-Seq"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              resetReview();
            }}
            disabled={loading}
            required
          />

          <Button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Processing..." : "Interpret criteria"}
          </Button>
        </div>

        <p className="form-note">
          BioNexus will identify the research goal, disease, organism, assay,
          and analysis criteria before searching for datasets.
        </p>
      </form>

      {loading && (
        <EmptyState title="Processing research request">
          {interpretation
            ? "Approving the reviewed criteria and searching NCBI/SRA."
            : "Interpreting your research question. Your existing dataset results will be preserved until a new search begins."}
        </EmptyState>
      )}

      {!loading && error && (
        <EmptyState title="Research request failed">
          <p>{error}</p>
          <p>
            Check that the BioNexus backend is running. If approval was
            rejected, review the criteria or clarify your research query.
          </p>
        </EmptyState>
      )}

      {!loading && interpretation && (
        <section className="dataset-results" aria-live="polite">
          <div className="dataset-results-heading">
            <div>
              <p className="eyebrow">RESEARCH INTENT</p>
              <h2>Review proposed criteria</h2>
              <p className="form-note">
                Check the interpretation before authorizing dataset discovery.
              </p>
            </div>
            <span className="dataset-accession">
              {formatStatus(interpretation.intent.review_status)}
            </span>
          </div>

          <div className="dataset-result-card">
            <div className="dataset-card-section">
              <h4>Interpreted research criteria</h4>

              <div className="dataset-metadata">
                {intentFields.map(({ key, label }) => {
                  const field = interpretation.intent[key];

                  return (
                    <div className="dataset-metadata-item" key={key}>
                      <span>{label}</span>
                      <strong>{displayField(field)}</strong>
                      <span>
                        Status: {formatStatus(field.status)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="dataset-card-section">
              <h4>Constraints</h4>
              {interpretation.intent.constraints.length > 0 ? (
                <ul className="dataset-evaluation-list">
                  {interpretation.intent.constraints.map((item, index) => (
                    <li key={`${index}-${item}`}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="form-note">No additional constraints specified.</p>
              )}
            </div>

            {interpretation.intent.clarification_required && (
              <div className="dataset-card-section">
                <h4>Clarification required</h4>
                <p>
                  The interpreted request needs clarification before approval.
                  Update your research query to resolve the questions below.
                </p>
              </div>
            )}

            {interpretation.intent.clarification_questions.length > 0 && (
              <div className="dataset-card-section">
                <h4>Questions to resolve</h4>
                <ul className="dataset-warning-list">
                  {interpretation.intent.clarification_questions.map(
                    (question, index) => (
                      <li key={`${index}-${question}`}>{question}</li>
                    ),
                  )}
                </ul>
              </div>
            )}

            {interpretation.source === "rules_fallback" && (
              <p className="form-note">
                Criteria were generated using the rules-based fallback rather
                than the AI interpretation provider.
              </p>
            )}

            {interpretation.warning && (
              <p className="form-note">{interpretation.warning}</p>
            )}

            <label className="form-note">
              <input
                type="checkbox"
                checked={confirmedForApproval}
                onChange={(event) =>
                  setConfirmedForApproval(event.target.checked)
                }
                disabled={
                  loading ||
                  interpretation.intent.clarification_required
                }
              />{" "}
              I have reviewed these criteria and authorize BioNexus to use
              them for dataset discovery.
            </label>

            <div className="form-row">
              <Button
                type="button"
                disabled={
                  loading ||
                  !confirmedForApproval ||
                  interpretation.intent.clarification_required
                }
                onClick={handleApproveAndSearch}
              >
                {loading ? "Processing..." : "Approve & search datasets"}
              </Button>
              <Button
                type="button"
                disabled={loading}
                onClick={() => {
                  resetReview();
                  setQuery((current) => current);
                }}
              >
                Revise query
              </Button>
            </div>
          </div>
        </section>
      )}

      {!loading && reviewMessage && (
        <EmptyState title="Research review">
          <p>{reviewMessage}</p>
          {reviewReasons.length > 0 && (
            <ul className="dataset-warning-list">
              {reviewReasons.map((reason, index) => (
                <li key={`${index}-${reason}`}>{reason}</li>
              ))}
            </ul>
          )}
          {reviewQuestions.length > 0 && (
            <div>
              <h4>Clarification questions</h4>
              <ul className="dataset-warning-list">
                {reviewQuestions.map((question, index) => (
                  <li key={`${index}-${question}`}>{question}</li>
                ))}
              </ul>
            </div>
          )}
        </EmptyState>
      )}

      {!loading &&
        !error &&
        hasSearched &&
        results.length === 0 &&
        !reviewMessage && (
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
              dataset.study_title || dataset.title || dataset.accession;

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
                    <p className="dataset-abstract">{dataset.title}</p>
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
                      <strong>{dataset.library_strategy || "Not reported"}</strong>
                    </div>
                    <div className="dataset-metadata-item">
                      <span>Library source</span>
                      <strong>{dataset.library_source || "Not reported"}</strong>
                    </div>
                    <div className="dataset-metadata-item">
                      <span>Experiment type</span>
                      <strong>{dataset.experiment_type || "Not reported"}</strong>
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
                          {experiment.title && <p>{experiment.title}</p>}
                          {experiment.organism && (
                            <p>
                              <strong>Organism:</strong> {experiment.organism}
                            </p>
                          )}

                          {experiment.samples.length > 0 ? (
                            experiment.samples.map((sample) => (
                              <div
                                className="dataset-sample"
                                key={sample.accession}
                              >
                                <p>
                                  <strong>Sample:</strong> {sample.accession}
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

      {!loading && !error && !hasSearched && !interpretation && (
        <EmptyState title="Ready to discover datasets">
          Enter a disease, organism, or sequencing query to interpret the
          research criteria before searching public datasets.
        </EmptyState>
      )}
    </div>
  );
}
