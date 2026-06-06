import clsx from "clsx";

interface MetricBarProps {
  label: string;
  value: number | string | null;
}

export function MetricBar({ label, value }: MetricBarProps) {
  const isNumber = typeof value === "number";
  const numValue = isNumber ? (value as number) : 0;
  const segmentsCount = Math.round(Math.max(0, Math.min(100, numValue)) / 10);

  const getSegmentColor = (idx: number) => {
    if (idx >= segmentsCount) return "bg-[#141820] border-white/[0.02]";
    if (numValue >= 80) return "bg-[#00f2ff] shadow-[0_0_4px_#00f2ff]"; // Neon Cyan
    if (numValue >= 55) return "bg-[#ffba20] shadow-[0_0_4px_#ffba20]"; // Warning Yellow
    return "bg-rose-500 shadow-[0_0_4px_rgba(239,68,68,0.5)]"; // Error Red
  };

  return (
    <div className="space-y-1 font-mono text-[10px]">
      <div className="flex justify-between items-center text-outline select-none uppercase">
        <span>{label}</span>
        <span className="font-bold text-on-surface">{isNumber ? `${numValue}%` : value ?? "?"}</span>
      </div>
      <div className="flex gap-[3px] h-1.5">
        {isNumber ? (
          Array(10)
            .fill(null)
            .map((_, i) => (
              <div
                key={i}
                className={clsx("flex-1 h-full border border-transparent transition-all", getSegmentColor(i))}
              />
            ))
        ) : (
          <div className="flex-1 bg-[#141820] border border-white/[0.02] h-full text-[7px] text-outline/30 flex items-center justify-center select-none uppercase">
            unresolved telemetry
          </div>
        )}
      </div>
    </div>
  );
}
