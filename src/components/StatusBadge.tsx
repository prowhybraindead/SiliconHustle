import clsx from "clsx";

import { labelize } from "../utils/format";

interface StatusBadgeProps {
  value: string | null | undefined;
  tone?: "blue" | "green" | "amber" | "red" | "neutral";
}

const toneClass = {
  blue: "border-tech-blue/40 bg-tech-blue/10 text-sky-200",
  green: "border-tech-green/40 bg-tech-green/10 text-green-200",
  amber: "border-tech-amber/40 bg-tech-amber/10 text-amber-200",
  red: "border-red-400/40 bg-red-500/10 text-red-200",
  neutral: "border-white/15 bg-white/5 text-slate-200",
};

export function StatusBadge({ value, tone = "neutral" }: StatusBadgeProps) {
  return <span className={clsx("inline-flex rounded px-2 py-1 text-[11px] font-semibold", toneClass[tone])}>{value ? labelize(value) : "?"}</span>;
}
