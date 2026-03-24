"use client";

import { use, Suspense, lazy } from "react";
import { useMatterDashboard, useTasks, useStakeholders } from "@/hooks";
import { usePermissions } from "@/hooks/use-permissions";
import { LoadingState } from "@/components/layout/LoadingState";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

// Core components loaded eagerly (above the fold)
import { MatterHeader } from "./_components/MatterHeader";
import { MetricsRow } from "./_components/MetricsRow";
import { AlertsPanel } from "./_components/AlertsPanel";
import { TasksByPhase } from "./_components/TasksByPhase";

// Below-the-fold and conditional components loaded lazily
const RecentActivity = lazy(() =>
  import("./_components/RecentActivity").then((m) => ({
    default: m.RecentActivity,
  })),
);
const AssetSummaryCard = lazy(() =>
  import("./_components/AssetSummaryCard").then((m) => ({
    default: m.AssetSummaryCard,
  })),
);
const StakeholdersCard = lazy(() =>
  import("./_components/StakeholdersCard").then((m) => ({
    default: m.StakeholdersCard,
  })),
);
const UpcomingDeadlinesCard = lazy(() =>
  import("./_components/UpcomingDeadlinesCard").then((m) => ({
    default: m.UpcomingDeadlinesCard,
  })),
);
const AIInsightsPanel = lazy(() =>
  import("./_components/AIInsightsPanel").then((m) => ({
    default: m.AIInsightsPanel,
  })),
);

function CardSkeleton() {
  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-20 w-full" />
      </CardContent>
    </Card>
  );
}

// Placeholder firmId — will come from context/auth in production
const FIRM_ID = "current";

export default function MatterDashboardPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);
  const { data: dashboard, isLoading, error } = useMatterDashboard(FIRM_ID, matterId);
  // Only fetch enough tasks for the dashboard phase summary (not the full list)
  const { data: tasksData } = useTasks(FIRM_ID, matterId, { per_page: 50 });
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);
  const { can, isReadOnly } = usePermissions(matterId);

  if (isLoading) {
    return <LoadingState variant="detail" />;
  }

  if (error || !dashboard) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-danger">Failed to load matter dashboard.</p>
          <p className="text-sm text-muted-foreground mt-1">
            The matter may not exist or you may not have access.
          </p>
        </CardContent>
      </Card>
    );
  }

  const { matter, task_summary, asset_summary, upcoming_deadlines, recent_events } = dashboard;
  const tasks = tasksData?.data ?? [];
  const stakeholders = stakeholdersData?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Matter Header */}
      <MatterHeader matter={matter} firmId={FIRM_ID} />

      {/* Key Metrics */}
      <MetricsRow
        taskSummary={task_summary}
        assetSummary={asset_summary}
        upcomingDeadlines={upcoming_deadlines}
      />

      {/* Alerts */}
      <AlertsPanel
        taskSummary={task_summary}
        upcomingDeadlines={upcoming_deadlines}
        matterId={matterId}
      />

      {/* Two-column layout */}
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Left column (60%) */}
        <div className="lg:col-span-3 space-y-6">
          <TasksByPhase
            tasks={tasks}
            firmId={FIRM_ID}
            matterId={matterId}
          />
          {/* Activity feed: hidden for beneficiary/read_only */}
          {can("event:read") && (
            <Suspense fallback={<CardSkeleton />}>
              <RecentActivity events={recent_events} matterId={matterId} />
            </Suspense>
          )}
        </div>

        {/* Right column (40%) */}
        <div className="lg:col-span-2 space-y-6">
          {/* AI Insights: visible to professionals/admins */}
          {can("task:create") && (
            <Suspense fallback={<CardSkeleton />}>
              <AIInsightsPanel firmId={FIRM_ID} matterId={matterId} />
            </Suspense>
          )}
          {/* Asset summary: hidden for read_only */}
          {!isReadOnly && (
            <Suspense fallback={<CardSkeleton />}>
              <AssetSummaryCard
                assetSummary={asset_summary}
                matterId={matterId}
              />
            </Suspense>
          )}
          <Suspense fallback={<CardSkeleton />}>
            <StakeholdersCard
              stakeholders={stakeholders}
              matterId={matterId}
            />
          </Suspense>
          <Suspense fallback={<CardSkeleton />}>
            <UpcomingDeadlinesCard
              deadlines={upcoming_deadlines}
              matterId={matterId}
            />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
