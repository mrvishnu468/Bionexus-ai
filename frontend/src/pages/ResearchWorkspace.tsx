import { useEffect, useState } from "react";

interface ResearchWorkspaceProps {
  researchId: string;
  question: string;
  status: string;
}

interface ResearchJob {
  research_id: string;
  question: string;
  status: string;
  message: string;
}

const API_BASE_URL = "http://127.0.0.1:8000";

function ResearchWorkspace({
  researchId,
  question,
  status: initialStatus,
}: ResearchWorkspaceProps) {
  const [status, setStatus] = useState(initialStatus);

  useEffect(() => {
    const fetchResearchStatus = async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/research/${researchId}`,
        );

        if (!response.ok) {
          return;
        }

        const researchJob: ResearchJob = await response.json();
        setStatus(researchJob.status);
      } catch {
        // Keep the current status if the backend is temporarily unavailable.
      }
    };

    fetchResearchStatus();

    const interval = setInterval(fetchResearchStatus, 1000);

    return () => clearInterval(interval);
  }, [researchId]);

  const stages = [
    ["planning", "Research planning"],
    ["dataset_discovery", "Dataset discovery"],
    ["dataset_evaluation", "Dataset evaluation"],
    ["analysis", "RNA-seq analysis"],
    ["pathways", "Pathway analysis"],
    ["literature", "Literature evidence"],
    ["scientific_review", "Scientific review"],
    ["report", "Final report"],
  ];

  const getStageState = (stage: string) => {
    const currentIndex = stages.findIndex(([value]) => value === status);
    const stageIndex = stages.findIndex(([value]) => value === stage);

    if (status === "queued") {
      return "waiting";
    }

    if (status === "completed") {
      return "completed";
    }

    if (stageIndex < currentIndex) {
      return "completed";
    }

    if (stageIndex === currentIndex) {
      return "active";
    }

    return "waiting";
  };

  return (
    <main>
      <h1>Research Workspace</h1>

      <section>
        <h2>Research Question</h2>
        <p>{question}</p>
      </section>

      <section>
        <h2>Research Status</h2>
        <p>{status}</p>
      </section>

      <section>
        <h2>Research ID</h2>
        <p>{researchId}</p>
      </section>

      <section>
        <h2>Research Pipeline</h2>

        <ol>
          {stages.map(([value, label]) => (
            <li key={value}>
              {label} — {getStageState(value)}
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

export default ResearchWorkspace;