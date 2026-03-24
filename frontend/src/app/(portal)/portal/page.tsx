"use client";

import { usePortalMatters } from "@/hooks/use-portal-queries";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Portal landing — lists matters where the user is a beneficiary.
 * If only one matter, could auto-redirect.
 */
export default function PortalLandingPage() {
  const { data, isLoading } = usePortalMatters();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  const matters = data?.matters ?? [];

  if (matters.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="rounded-full bg-muted/50 p-6 mb-6">
          <div className="size-12 rounded-full bg-primary/10" />
        </div>
        <h2 className="text-xl font-serif font-medium text-foreground mb-2">
          No estates found
        </h2>
        <p className="text-muted-foreground max-w-md">
          You don&apos;t have access to any estates at this time. If you believe this is
          an error, please contact your estate administrator.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-serif font-medium text-foreground">
          Your Estates
        </h1>
        <p className="mt-2 text-muted-foreground">
          Select an estate to view its progress and details.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {matters.map((m) => (
          <Link
            key={m.matter_id}
            href={`/portal/${m.matter_id}`}
            className="group rounded-xl border border-border/50 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:border-primary/20"
          >
            <p className="text-xs font-medium uppercase tracking-wider text-primary/70 mb-1">
              {m.firm_name}
            </p>
            <h3 className="text-lg font-serif font-medium text-foreground group-hover:text-primary transition-colors">
              Estate of {m.decedent_name}
            </h3>
            <p className="mt-2 text-sm text-muted-foreground capitalize">
              Phase: {m.phase.replace("_", " ")}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
