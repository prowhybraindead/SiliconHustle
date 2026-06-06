import React from "react";

interface ConsolePanelProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  className?: string;
  variant?: "z-1" | "z-2" | "z-2-active";
}

export function ConsolePanel({
  children,
  className = "",
  variant = "z-1",
  ...props
}: ConsolePanelProps) {
  const baseClass =
    variant === "z-2-active"
      ? "z-2-panel z-2-panel-active"
      : variant === "z-2"
      ? "z-2-panel"
      : "z-1-panel";

  return (
    <div className={`${baseClass} p-gutter ${className}`} {...props}>
      {children}
    </div>
  );
}
