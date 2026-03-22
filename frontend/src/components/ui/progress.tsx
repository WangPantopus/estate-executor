import * as React from "react";
import { cn } from "@/lib/utils";

interface ProgressProps extends React.ComponentProps<"div"> {
  value?: number;
  max?: number;
}

function Progress({ className, value = 0, max = 100, ...props }: ProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-surface-elevated",
        className,
      )}
      {...props}
    >
      <div
        className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

export { Progress };
