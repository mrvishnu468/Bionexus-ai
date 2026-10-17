import { WorkspacePlaceholder } from "../components/WorkspacePlaceholder";

export function AnalysisPage() {
  return (
    <WorkspacePlaceholder
      kicker="Analysis"
      title="Bioinformatics analysis"
      description="Analysis outputs will appear here when a real workflow writes them. The current backend research stages are status simulation only."
      emptyTitle="No analysis results"
      emptyBody="RNA-seq processing is not implemented. This workspace will not show mock differential expression or QC metrics."
    />
  );
}
