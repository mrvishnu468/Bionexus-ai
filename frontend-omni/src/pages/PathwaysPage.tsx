import { WorkspacePlaceholder } from "../components/WorkspacePlaceholder";

export function PathwaysPage() {
  return (
    <WorkspacePlaceholder
      kicker="Pathways"
      title="Pathways and networks"
      description="Pathway enrichment and network views belong here after analysis artifacts exist."
      emptyTitle="No pathway results"
      emptyBody="KEGG and related tools are not wired. No enrichment tables or networks are displayed."
    />
  );
}
