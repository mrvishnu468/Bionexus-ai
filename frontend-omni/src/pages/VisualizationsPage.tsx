import { WorkspacePlaceholder } from "../components/WorkspacePlaceholder";

export function VisualizationsPage() {
  return (
    <WorkspacePlaceholder
      kicker="Figures"
      title="Visualizations"
      description="Figures generated from connected jobs will be collected in this workspace."
      emptyTitle="No figures available"
      emptyBody="There is no plotting service and no stored figure files to render."
    />
  );
}
