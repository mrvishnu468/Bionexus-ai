type StatusTone = "neutral" | "unavailable";

interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
}

export function StatusBadge({
  label,
  tone = "unavailable",
}: StatusBadgeProps) {
  return <span className={`status-badge status-badge-${tone}`}>{label}</span>;
}
