import { useState } from "react";
import { startResearch } from "../services/researchApi";
import ResearchWorkspace from "./ResearchWorkspace";

function Home() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [research, setResearch] = useState<{
    researchId: string;
    question: string;
    status: string;
  } | null>(null);

  async function handleStartResearch() {
    if (!question.trim()) {
      setError("Please enter a research question.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await startResearch(question.trim());

      setResearch({
        researchId: result.research_id,
        question: result.question,
        status: result.status,
      });
    } catch {
      setError("Unable to start the research investigation.");
    } finally {
      setLoading(false);
    }
  }

  if (research) {
    return (
      <ResearchWorkspace
        researchId={research.researchId}
        question={research.question}
        status={research.status}
      />
    );
  }

  return (
    <main>
      <h1>BioNexus AI</h1>

      <p>
        Evidence-grounded AI research assistant for bioinformatics.
      </p>

      <section>
        <h2>Start a Research Investigation</h2>

        <p>
          Ask a biological research question and let BioNexus build a
          reproducible research workflow.
        </p>

        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Example: Find a suitable recent human RNA-seq dataset for Alzheimer's disease..."
          rows={6}
        />

        <br />

        <button onClick={handleStartResearch} disabled={loading}>
          {loading ? "Starting Research..." : "Start Research"}
        </button>

        {error && <p>{error}</p>}
      </section>
    </main>
  );
}

export default Home;