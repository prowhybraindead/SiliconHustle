import React from "react";

interface StatusChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  label: string;
  variant?: "success" | "warning" | "error" | "neutral";
  className?: string;
}

export function StatusChip({
  label,
  variant = "neutral",
  className = "",
  ...props
}: StatusChipProps) {
  let colors = "bg-white/5 border-white/10 text-on-surface";
  if (variant === "success") {
    colors = "bg-primary-container/10 border-primary-container/30 text-primary-container";
  } else if (variant === "warning") {
    colors = "bg-secondary-container/10 border-secondary-fixed-dim/30 text-secondary-fixed-dim";
  } else if (variant === "error") {
    colors = "bg-error-container/20 border-error/30 text-error";
  }

  return (
    <span
      className={`inline-flex items-center justify-center font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 border rounded-sm ${colors} ${className}`}
      {...props}
    >
      [{label}]
    </span>
  );
}
