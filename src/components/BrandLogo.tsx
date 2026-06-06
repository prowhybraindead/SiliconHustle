import { useMemo, useState } from "react";

import type { Brand } from "../types/game";

interface BrandLogoProps {
  brand?: Brand | null;
  logoUrl?: string | null;
  name?: string | null;
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "h-8 w-8 text-[10px]",
  md: "h-10 w-10 text-xs",
  lg: "h-12 w-12 text-sm",
};

export function BrandLogo({ brand, logoUrl, name, size = "md" }: BrandLogoProps) {
  const [failed, setFailed] = useState(false);
  const label = brand?.name ?? name ?? "Brand";
  const src = brand?.logo_url ?? logoUrl ?? null;
  const initials = useMemo(
    () =>
      label
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join("") || "?",
    [label],
  );

  if (src && !failed) {
    return (
      <div className={`${sizeClasses[size]} flex shrink-0 items-center justify-center rounded border border-white/10 bg-white`}>
        <img alt={`${label} logo`} className="max-h-[72%] max-w-[72%] object-contain" onError={() => setFailed(true)} src={src} />
      </div>
    );
  }

  return (
    <div className={`${sizeClasses[size]} flex shrink-0 items-center justify-center rounded border border-tech-blue/25 bg-tech-blue/10 font-semibold text-tech-blue`}>
      {initials}
    </div>
  );
}
