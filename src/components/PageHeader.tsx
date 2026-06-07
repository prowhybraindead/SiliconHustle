import type { ReactNode } from "react";
import { translateUiText } from "../utils/format";

interface PageHeaderProps {
  title: string;
  eyebrow?: string;
  action?: ReactNode;
}

export function PageHeader({ title, eyebrow, action }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-tech-blue">{translateUiText(eyebrow)}</div> : null}
        <h1 className="text-2xl font-semibold text-white">{translateUiText(title)}</h1>
      </div>
      {action ? <div>{action}</div> : null}
    </div>
  );
}
