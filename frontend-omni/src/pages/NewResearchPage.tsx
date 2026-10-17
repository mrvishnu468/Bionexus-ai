import { Button } from "../components/Button";
import { PageHeader } from "../components/PageHeader";

export function NewResearchPage() {
  return (
    <div className="page-stack">
      <PageHeader
        kicker="Research"
        title="Start an investigation"
        description="Enter a biological question. Job creation is reserved for a later milestone and will call POST /api/research without simulating analysis results."
      />

      <form
        className="workspace-form"
        onSubmit={(event) => event.preventDefault()}
      >
        <label htmlFor="research-question">Research question</label>
        <textarea
          id="research-question"
          rows={7}
          placeholder="Example: Find a suitable recent human RNA-seq dataset for Alzheimer's disease."
          disabled
        />
        <p className="form-note">
          The form is visible so the workspace is ready, but it is disabled
          until the research API client is connected.
        </p>
        <Button type="submit" disabled>
          Start research
        </Button>
      </form>
    </div>
  );
}
