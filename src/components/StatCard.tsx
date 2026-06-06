interface StatCardProps {
  label: string;
  value: string | number;
  accent?: "blue" | "green" | "amber";
}

const accentClass = {
  blue: "text-tech-blue",
  green: "text-tech-green",
  amber: "text-tech-amber",
};

export function StatCard({ label, value, accent = "blue" }: StatCardProps) {
  return (
    <div className="panel rounded-lg p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-2 truncate font-mono text-2xl font-semibold ${accentClass[accent]}`}>{value}</div>
    </div>
  );
}
