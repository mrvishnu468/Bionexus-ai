import { WorkspacePlaceholder } from "../components/WorkspacePlaceholder";

export function KnowledgePage() {
  return (
    <WorkspacePlaceholder
      kicker="Knowledge"
      title="Knowledge"
      description="Retained findings and prior investigations will live here after persistence exists."
      emptyTitle="Knowledge store is empty"
      emptyBody="Jobs are in-memory on the backend and this client does not load them. Nothing is cached locally."
    />
  );
}
