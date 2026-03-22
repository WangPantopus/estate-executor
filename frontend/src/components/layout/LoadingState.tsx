import * as React from "react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

interface LoadingStateProps {
  variant?: "cards" | "table" | "detail" | "list";
  count?: number;
  className?: string;
}

export function LoadingState({
  variant = "cards",
  count = 3,
  className,
}: LoadingStateProps) {
  if (variant === "table") {
    return (
      <div className={cn("space-y-3", className)}>
        {/* Table header */}
        <div className="flex items-center gap-4 px-4 py-3">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-16 ml-auto" />
        </div>
        {/* Table rows */}
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-4 rounded-lg border border-border bg-card px-4 py-4"
          >
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-6 w-20 rounded-full" />
            <Skeleton className="h-4 w-20 ml-auto" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "detail") {
    return (
      <div className={cn("space-y-6", className)}>
        <div className="space-y-2">
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-border bg-card p-6 space-y-3">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-6 w-32" />
            </div>
          ))}
        </div>
        <div className="rounded-lg border border-border bg-card p-6 space-y-4">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </div>
    );
  }

  if (variant === "list") {
    return (
      <div className={cn("space-y-2", className)}>
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3"
          >
            <Skeleton className="h-9 w-9 rounded-full" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  // Cards variant (default)
  return (
    <div className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-3", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border border-border bg-card p-6 space-y-4"
        >
          <div className="space-y-2">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-2/3" />
          </div>
          <div className="flex gap-2 pt-2">
            <Skeleton className="h-6 w-20 rounded-full" />
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}
