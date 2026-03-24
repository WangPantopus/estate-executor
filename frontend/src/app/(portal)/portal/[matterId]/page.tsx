"use client";

import { useParams } from "next/navigation";
import { usePortalOverview } from "@/hooks/use-portal-queries";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Check, Clock, Mail, User, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export default function PortalOverviewPage() {
  const params = useParams();
  const matterId = params.matterId as string;
  const { data, isLoading } = usePortalOverview(matterId);

  if (isLoading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-12 w-96" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-16">
        <p className="text-muted-foreground">Unable to load estate information.</p>
      </div>
    );
  }

  const { matter, contacts, milestones, distribution } = data;

  return (
    <div className="space-y-10">
      {/* Hero Header */}
      <div className="text-center sm:text-left">
        {data.firm_name && (
          <p className="text-xs font-medium uppercase tracking-wider text-primary/70 mb-2">
            {data.firm_name}
          </p>
        )}
        <h1 className="text-3xl sm:text-4xl font-serif font-medium text-foreground">
          Estate of {matter.decedent_name}
        </h1>
        <p className="mt-3 text-muted-foreground">
          We&apos;re working to settle this estate as efficiently as possible. Here&apos;s
          the current status.
        </p>
      </div>

      {/* Phase Progress */}
      <Card className="border-border/40 shadow-sm">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-foreground">Overall Progress</p>
            <span className="text-sm font-medium text-primary">
              {matter.completion_percentage}%
            </span>
          </div>
          <Progress value={matter.completion_percentage} className="h-2" />
          <p className="mt-2 text-xs text-muted-foreground capitalize">
            Current phase: {matter.phase.replace("_", " ")}
          </p>
        </CardContent>
      </Card>

      {/* Key Info Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        {/* Completion status */}
        <Card className="border-border/40 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex size-10 items-center justify-center rounded-full bg-primary/10">
                <Clock className="size-5 text-primary" />
              </div>
              <p className="text-sm font-medium text-foreground">Status</p>
            </div>
            <p className="text-2xl font-serif font-medium text-foreground">
              {matter.completion_percentage}%
            </p>
            <p className="text-xs text-muted-foreground mt-1">Estimated completion</p>
          </CardContent>
        </Card>

        {/* Your role */}
        <Card className="border-border/40 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex size-10 items-center justify-center rounded-full bg-emerald-50">
                <User className="size-5 text-emerald-600" />
              </div>
              <p className="text-sm font-medium text-foreground">Your Role</p>
            </div>
            <p className="text-2xl font-serif font-medium text-foreground">
              {data.your_role}
            </p>
            {data.your_relationship && (
              <p className="text-xs text-muted-foreground mt-1">{data.your_relationship}</p>
            )}
          </CardContent>
        </Card>

        {/* Lead contact */}
        <Card className="border-border/40 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex size-10 items-center justify-center rounded-full bg-blue-50">
                <Mail className="size-5 text-blue-600" />
              </div>
              <p className="text-sm font-medium text-foreground">Your Contact</p>
            </div>
            {contacts.length > 0 ? (
              <>
                <p className="text-lg font-medium text-foreground">{contacts[0].name}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {contacts[0].role}
                </p>
                <a
                  href={`mailto:${contacts[0].email}`}
                  className="text-xs text-primary hover:underline mt-0.5 inline-block"
                >
                  {contacts[0].email}
                </a>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Contact info pending</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Milestone Timeline */}
      <div>
        <h2 className="text-xl font-serif font-medium text-foreground mb-6">
          Milestones
        </h2>
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[15px] top-2 bottom-2 w-px bg-border" />

          <div className="space-y-6">
            {milestones.map((milestone, i) => (
              <div key={i} className="relative flex items-start gap-4 pl-0">
                {/* Dot */}
                <div
                  className={cn(
                    "relative z-10 flex size-[30px] shrink-0 items-center justify-center rounded-full border-2",
                    milestone.completed
                      ? "border-emerald-500 bg-emerald-50"
                      : milestone.is_next
                        ? "border-primary bg-primary/10 animate-pulse"
                        : "border-border bg-white",
                  )}
                >
                  {milestone.completed ? (
                    <Check className="size-4 text-emerald-600" />
                  ) : milestone.is_next ? (
                    <ArrowRight className="size-3.5 text-primary" />
                  ) : (
                    <div className="size-2 rounded-full bg-border" />
                  )}
                </div>

                {/* Content */}
                <div className="pt-0.5">
                  <p
                    className={cn(
                      "text-sm font-medium",
                      milestone.completed
                        ? "text-foreground"
                        : milestone.is_next
                          ? "text-primary"
                          : "text-muted-foreground",
                    )}
                  >
                    {milestone.title}
                    {milestone.completed && (
                      <span className="ml-2 text-emerald-600">&#10003;</span>
                    )}
                  </p>
                  {milestone.date && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {milestone.date}
                    </p>
                  )}
                  {milestone.is_next && (
                    <Badge variant="outline" className="mt-1.5 text-xs border-primary/30 text-primary">
                      Current step
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Distribution Summary */}
      {(distribution.notices_count > 0 || distribution.distribution_status !== "pending") && (
        <div>
          <h2 className="text-xl font-serif font-medium text-foreground mb-4">
            Distribution
          </h2>
          <Card className="border-border/40 shadow-sm">
            <CardContent className="p-6">
              <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground mb-1">
                    Distribution Status
                  </p>
                  <Badge
                    variant="outline"
                    className={cn(
                      "capitalize",
                      distribution.distribution_status === "completed"
                        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                        : distribution.distribution_status === "in_progress"
                          ? "border-blue-200 bg-blue-50 text-blue-700"
                          : "border-amber-200 bg-amber-50 text-amber-700",
                    )}
                  >
                    {distribution.distribution_status.replace("_", " ")}
                  </Badge>
                </div>

                {distribution.notices_count > 0 && (
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">
                      {distribution.notices_count} notice{distribution.notices_count !== 1 ? "s" : ""}
                    </p>
                    {distribution.pending_acknowledgments > 0 && (
                      <p className="text-xs text-amber-600 mt-0.5">
                        {distribution.pending_acknowledgments} pending your acknowledgment
                      </p>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
