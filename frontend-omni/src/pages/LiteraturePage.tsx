import { WorkspacePlaceholder } from "../components/WorkspacePlaceholder";

export function LiteraturePage() {
  return (
    <WorkspacePlaceholder
      kicker="Evidence"
      title="Literature"
      description="PubMed and related evidence will attach to a research job rather than appear as a standalone simulated feed."
      emptyTitle="No literature attached"
      emptyBody="The literature tool package is empty on the backend. This page does not list placeholder papers."
    />
  );
}
