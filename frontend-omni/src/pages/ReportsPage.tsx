import { WorkspacePlaceholder } from "../components/WorkspacePlaceholder";

export function ReportsPage() {
  return (
    <WorkspacePlaceholder
      kicker="Reports"
      title="Scientific reports"
      description="Final reports will be shown when the research workflow writes a real report artifact."
      emptyTitle="No reports generated"
      emptyBody="The current research workflow only advances a status field. There is no report document to open."
    />
  );
}
