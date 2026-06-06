import React from "react";

interface StationBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  label: string;
  status?: string;
  className?: string;
}

export function StationBadge({
  label,
  status = "OPERATIONAL",
  className = "",
  ...props
}: StationBadgeProps) {
  return (
    <span
      className={`inline-flex flex-col items-center justify-center font-mono ${className}`}
      {...props}
    >
      <span className="text-[10px] uppercase tracking-[0.05em] text-secondary-fixed-dim">
        {label}
      </span>
      <span className="text-[8px] uppercase tracking-widest text-primary-container/80">
        [{status}]
      </span>
    </span>
  );
}
