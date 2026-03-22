import * as React from "react";
import { cn } from "@/lib/utils";

function Skeleton({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "rounded-md skeleton-shimmer",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };
