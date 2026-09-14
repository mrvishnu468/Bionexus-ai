import { useState } from "react";
import { searchDatasets } from "../services/datasetApi";

function Datasets() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<any[]>([]);

  async function handleSearch() {
    if (!query.trim()) {
      setError("Please enter a dataset search query.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await searchDatasets(query.trim());
      setResults(response.datasets ?? []);
    } catch {
      setError("Unable to search datasets.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Dataset Discovery</h1>

      <p>
        Find and evaluate biological datasets from NCBI/SRA.
      </p>

      <section>
        <h2>Search Datasets</h2>

        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Example: Alzheimer disease Homo sapiens RNA-Seq"
        />

        <button onClick={handleSearch} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>

        {error && <p>{error}</p>}
      </section>

      <section>
        <h2>Results</h2>

        {results.map((result) => (
          <article key={result.dataset.accession}>
            <h3>{result.dataset.study_accession}</h3>

            <p>
              {result.dataset.study_title ||
                result.dataset.title ||
                "Untitled study"}
            </p>

            <p>
              Samples: {result.dataset.sample_count ?? "Unknown"} | Runs:{" "}
              {result.dataset.run_count ?? "Unknown"}
            </p>

            <p>
              Assay: {result.evaluation.assay_type}
            </p>

            <p>
              Suitability: {result.evaluation.suitability}
            </p>

            <p>
              Score: {result.evaluation.score}
            </p>
          </article>
        ))}
      </section>
    </main>
  );
}

export default Datasets;