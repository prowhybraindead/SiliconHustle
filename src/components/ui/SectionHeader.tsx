import React from "react";
import { translateUiText } from "../../utils/format";

interface SectionHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  className?: string;
}

export function SectionHeader({
  title,
  subtitle,
  className = "",
  ...props
}: SectionHeaderProps) {
  return (
    <div
      className={`bg-surface-container border border-white/10 rounded-none p-4 relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-end gap-2 ${className}`}
      {...props}
    >
      <div className="absolute inset-0 bg-gradient-to-r from-primary-container/5 to-transparent pointer-events-none" />
      <div className="z-10">
        <h1 className="font-sans text-lg font-bold text-on-surface uppercase tracking-wider">
          {title}
        </h1>
        {subtitle && (
          <p className="font-mono text-[10px] uppercase tracking-wider text-outline mt-1">
            {translateUiText(subtitle)}
          </p>
        )}
      </div>
    </div>
  );
}
