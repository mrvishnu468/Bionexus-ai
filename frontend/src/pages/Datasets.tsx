import { useState } from "react";
import {
  searchDatasets,
  type DatasetSearchResult,
  type DatasetSuitability,
} from "../services/datasetApi";

function formatAssayType(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function suitabilityLabel(value: DatasetSuitability) {
  if (value === "recommended") {
    return "Recommended";
  }

  if (value === "conditional") {
    return "Conditional";
  }

  return "Not Recommended";
}

function suitabilityClass(value: DatasetSuitability) {
  return `suitability suitability-${value}`;
}

function DatasetCard({
  result,
}: {
  result: DatasetSearchResult;
}) {
  const { dataset, evaluation } = result;
  const [expanded, setExpanded] = useState(false);

  return (
    <article className="dataset-card">
      <div className="dataset-card-header">
        <div>
          <span className="dataset-label">SRA STUDY</span>
          <h3>{dataset.accession}</h3>
        </div>

        <div className={suitabilityClass(evaluation.suitability)}>
          {suitabilityLabel(evaluation.suitability)}
        </div>
      </div>

      <h4>
        {dataset.study_title ||
          dataset.title ||
          "Untitled study"}
      </h4>

      <div className="dataset-score">
        <strong>{evaluation.score}</strong>
        <span>/ 100 suitability</span>
      </div>

      <div className="dataset-metrics">
        <div>
          <span>Samples</span>
          <strong>
            {dataset.sample_count ?? "Unknown"}
          </strong>
        </div>

        <div>
          <span>Runs</span>
          <strong>
            {dataset.run_count ?? "Unknown"}
          </strong>
        </div>

        <div>
          <span>Experiments</span>
          <strong>{dataset.experiments.length}</strong>
        </div>

        <div>
          <span>Assay</span>
          <strong>
            {formatAssayType(evaluation.assay_type)}
          </strong>
        </div>
      </div>

      <div className="dataset-reasons">
        <h5>Evaluation</h5>

        {evaluation.reasons.map((reason) => (
          <p key={reason}>✓ {reason}</p>
        ))}

        {evaluation.warnings.length > 0 && (
          <div className="dataset-warnings">
            <h5>Scientific warnings</h5>

            {evaluation.warnings.map((warning) => (
              <p key={warning}>⚠ {warning}</p>
            ))}
          </div>
        )}
      </div>

      <button
        className="dataset-expand-button"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded
          ? "Hide study hierarchy"
          : "View study hierarchy"}
      </button>

      {expanded && (
        <div className="dataset-hierarchy">
          <div>
            <span>Study</span>
            <strong>{dataset.accession}</strong>
          </div>

          {dataset.experiments.map((experiment) => (
            <div
              className="experiment-node"
              key={experiment.accession}
            >
              <span>Experiment</span>
              <strong>{experiment.accession}</strong>

              {experiment.samples.map((sample) => (
                <div
                  className="sample-node"
                  key={sample.accession}
                >
                  <span>Sample</span>
                  <strong>{sample.accession}</strong>

                  {sample.runs.map((run) => (
                    <div
                      className="run-node"
                      key={run.accession}
                    >
                      <span>Run</span>
                      <strong>{run.accession}</strong>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

function Datasets() {
  const [query, setQuery] = useState(
    "Alzheimer disease Homo sapiens RNA-Seq",
  );
  const [results, setResults] = useState<DatasetSearchResult[]>(
    [],
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch() {
    if (!query.trim()) {
      setError("Enter a biological dataset search query.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await searchDatasets(
        query.trim(),
        10,
      );

      setResults(response.datasets);
    } catch {
      setError(
        "Unable to search NCBI/SRA right now. Check that the backend is running.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="datasets-page">
      <header className="datasets-header">
        <div>
          <span className="page-kicker">
            DATASET DISCOVERY
          </span>

          <h1>Find research datasets</h1>

          <p>
            Search NCBI/SRA and evaluate studies before
            downstream bioinformatics analysis.
          </p>
        </div>
      </header>

      <section className="dataset-search-panel">
        <label htmlFor="dataset-query">
          Research query
        </label>

        <div className="dataset-search-row">
          <input
            id="dataset-query"
            value={query}
            onChange={(event) =>
              setQuery(event.target.value)
            }
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleSearch();
              }
            }}
            placeholder="Example: Alzheimer disease Homo sapiens RNA-Seq"
          />

          <button
            onClick={handleSearch}
            disabled={loading}
          >
            {loading ? "Searching..." : "Search SRA"}
          </button>
        </div>

        {error && (
          <p className="dataset-error">{error}</p>
        )}
      </section>

      <section className="dataset-results-header">
        <div>
          <span className="page-kicker">
            SEARCH RESULTS
          </span>

          <h2>
            {results.length > 0
              ? `${results.length} studies found`
              : "No studies loaded"}
          </h2>
        </div>
      </section>

      <section className="dataset-results">
        {results.map((result) => (
          <DatasetCard
            key={result.dataset.accession}
            result={result}
          />
        ))}

        {!loading && results.length === 0 && (
          <div className="dataset-empty">
            <strong>Ready for dataset discovery</strong>
            <p>
              Enter a biological research question or
              dataset description above.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}

export default Datasets;