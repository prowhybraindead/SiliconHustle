import { StatusChip } from "./ui/StatusChip";

interface RiskBadgeProps {
  value: string | null | undefined;
}

export function RiskBadge({ value }: RiskBadgeProps) {
  const variant =
    value === "CRITICAL" || value === "HIGH"
      ? "error"
      : value === "MEDIUM"
      ? "warning"
      : value === "LOW"
      ? "success"
      : "neutral";

  return <StatusChip label={`RISK: ${value ?? "UNKNOWN"}`} variant={variant} />;
}
