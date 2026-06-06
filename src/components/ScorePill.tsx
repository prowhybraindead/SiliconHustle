interface ScorePillProps {
  label: string;
  value: number | null;
}

export function ScorePill({ label, value }: ScorePillProps) {
  const variant =
    value === null
      ? "text-outline/40 border-white/5 bg-[#090b0e]/30"
      : value >= 75
      ? "text-primary-container border-primary-container/25 bg-primary-container/5"
      : value >= 55
      ? "text-[#ffba20] border-[#ffba20]/25 bg-[#ffba20]/5"
      : "text-rose-400 border-rose-500/25 bg-rose-500/5";

  return (
    <div className={`font-mono text-[9px] uppercase border px-2 py-1.5 flex justify-between items-center select-none ${variant}`}>
      <span>{label}</span>
      <span className="font-bold">{value ?? "?"}</span>
    </div>
  );
}
