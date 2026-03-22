import * as React from "react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 px-6 text-center",
        className
      )}
    >
      {icon ? (
        <div className="mb-4 text-muted-foreground/40">{icon}</div>
      ) : (
        <svg
          className="mb-4 size-16 text-muted-foreground/20"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <rect
            x="8"
            y="12"
            width="48"
            height="40"
            rx="4"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <path
            d="M8 22h48"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <rect
            x="16"
            y="30"
            width="20"
            height="2"
            rx="1"
            fill="currentColor"
            opacity="0.5"
          />
          <rect
            x="16"
            y="36"
            width="14"
            height="2"
            rx="1"
            fill="currentColor"
            opacity="0.3"
          />
          <rect
            x="16"
            y="42"
            width="24"
            height="2"
            rx="1"
            fill="currentColor"
            opacity="0.2"
          />
        </svg>
      )}
      <h3 className="text-base font-medium text-foreground">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm text-muted-foreground leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
