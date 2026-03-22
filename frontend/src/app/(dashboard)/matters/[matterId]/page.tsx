"use client";

import { use } from "react";
import { useMatterDashboard, useTasks, useStakeholders } from "@/hooks";
import { LoadingState } from "@/components/layout/LoadingState";
import { Card, CardContent } from "@/components/ui/card";
import { MatterHeader } from "./_components/MatterHeader";
import { MetricsRow } from "./_components/MetricsRow";
import { TasksByPhase } from "./_components/TasksByPhase";
import { RecentActivity } from "./_components/RecentActivity";
import { AssetSummaryCard } from "./_components/AssetSummaryCard";
import { StakeholdersCard } from "./_components/StakeholdersCard";
import { UpcomingDeadlinesCard } from "./_components/UpcomingDeadlinesCard";
import { AlertsPanel } from "./_components/AlertsPanel";

// Placeholder firmId — will come from context/auth in production
const FIRM_ID = "current";

export default function MatterDashboardPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);
  const { data: dashboard, isLoading, error } = useMatterDashboard(FIRM_ID, matterId);
  const { data: tasksData } = useTasks(FIRM_ID, matterId, { per_page: 100 });
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);

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
          <RecentActivity events={recent_events} matterId={matterId} />
        </div>

        {/* Right column (40%) */}
        <div className="lg:col-span-2 space-y-6">
          <AssetSummaryCard
            assetSummary={asset_summary}
            matterId={matterId}
          />
          <StakeholdersCard
            stakeholders={stakeholders}
            firmId={FIRM_ID}
            matterId={matterId}
          />
          <UpcomingDeadlinesCard
            deadlines={upcoming_deadlines}
            matterId={matterId}
          />
        </div>
      </div>
    </div>
  );
}
