import { PageHeader } from "./PageHeader";
import { EmptyState } from "./EmptyState";

interface WorkspacePlaceholderProps {
  kicker: string;
  title: string;
  description: string;
  emptyTitle: string;
  emptyBody: string;
}

export function WorkspacePlaceholder({
  kicker,
  title,
  description,
  emptyTitle,
  emptyBody,
}: WorkspacePlaceholderProps) {
  return (
    <div className="page-stack">
      <PageHeader kicker={kicker} title={title} description={description} />
      <EmptyState title={emptyTitle}>{emptyBody}</EmptyState>
    </div>
  );
}
