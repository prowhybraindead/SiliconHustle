import { StatusBadge } from "./StatusBadge";

export function DataConfidenceBadge({ value }: { value?: string | null }) {
  const tone = value === "OFFICIAL" ? "green" : value === "RETAILER" ? "blue" : value === "MANUAL" ? "amber" : "neutral";
  return <StatusBadge value={value ?? "UNKNOWN_DATA"} tone={tone} />;
}
