import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  children: ReactNode;
}

export function EmptyState({ title, children }: EmptyStateProps) {
  return (
    <div className="ui-empty">
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}
