import { WorkspacePlaceholder } from "../components/WorkspacePlaceholder";

export function GeneResearchPage() {
  return (
    <WorkspacePlaceholder
      kicker="Genes"
      title="Gene research"
      description="Use this workspace for gene-centered follow-up once a research job has selected datasets and produced evidence."
      emptyTitle="No gene evidence yet"
      emptyBody="There is no connected gene lookup, expression table, or literature set. This page does not invent gene lists."
    />
  );
}
