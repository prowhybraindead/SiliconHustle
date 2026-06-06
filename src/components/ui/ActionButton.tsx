import React from "react";

interface ActionButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: "primary" | "secondary" | "danger";
  className?: string;
}

export function ActionButton({
  children,
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ActionButtonProps) {
  let baseStyle = "w-full h-10 font-mono text-xs uppercase tracking-wider rounded-none flex items-center justify-center gap-2 transition-all active:scale-95 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed disabled:active:scale-100";
  
  if (variant === "primary") {
    baseStyle += " bg-primary-container text-on-primary-fixed hover:bg-primary-fixed-dim";
  } else if (variant === "secondary") {
    baseStyle += " border border-primary-container text-primary-container bg-transparent hover:bg-primary-container/10";
  } else if (variant === "danger") {
    baseStyle += " bg-error-container text-on-error-container hover:bg-error hover:text-on-error";
  }

  return (
    <button className={`${baseStyle} ${className}`} type={type} {...props}>
      {children}
    </button>
  );
}
