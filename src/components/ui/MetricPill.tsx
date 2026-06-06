import React from "react";

interface MetricPillProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string | number;
  className?: string;
}

export function MetricPill({
  label,
  value,
  className = "",
  ...props
}: MetricPillProps) {
  return (
    <div
      className={`z-1-panel p-3 flex flex-col justify-center items-center rounded-none relative overflow-hidden ${className}`}
      {...props}
    >
      <span className="font-mono text-[9px] uppercase tracking-wider text-outline mb-1">
        {label}
      </span>
      <span className="font-mono text-sm font-bold text-primary-fixed-dim">
        {value}
      </span>
    </div>
  );
}
