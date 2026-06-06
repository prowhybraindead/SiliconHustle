import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

interface ModuleCardProps {
  title: string;
  subtitle: string;
  to: string;
  icon: LucideIcon;
  disabled?: boolean;
}

export function ModuleCard({ title, subtitle, to, icon: Icon, disabled }: ModuleCardProps) {
  const content = (
    <div className="panel group h-full rounded-lg p-4 transition hover:border-tech-blue/40 hover:bg-panel-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-100">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">{subtitle}</p>
        </div>
        <Icon className="h-5 w-5 text-tech-blue transition group-hover:text-white" />
      </div>
    </div>
  );

  if (disabled) {
    return <div className="cursor-not-allowed opacity-60">{content}</div>;
  }
  return <Link to={to}>{content}</Link>;
}
