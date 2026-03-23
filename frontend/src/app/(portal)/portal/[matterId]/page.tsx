"use client";

import { use } from "react";
import {
  useMatterDashboard,
  useTasks,
  useStakeholders,
  useCommunications,
  useEvents,
} from "@/hooks";
import { LoadingState } from "@/components/layout/LoadingState";
import { Card, CardContent } from "@/components/ui/card";
import { PhaseProgress } from "./_components/PhaseProgress";
import { InfoCards } from "./_components/InfoCards";
import { MilestoneTimeline } from "./_components/MilestoneTimeline";
import { DistributionSummary } from "./_components/DistributionSummary";

const FIRM_ID = "current";

export default function PortalOverviewPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);
  const { data: dashboard, isLoading, error } = useMatterDashboard(FIRM_ID, matterId);
  const { data: tasksData } = useTasks(FIRM_ID, matterId, { per_page: 200 });
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);
  const { data: commsData } = useCommunications(FIRM_ID, matterId);
  const { data: eventsData } = useEvents(FIRM_ID, matterId, { per_page: 50 });

  if (isLoading) {
    return <LoadingState variant="detail" />;
  }

  if (error || !dashboard) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-danger">Unable to load estate information.</p>
          <p className="text-sm text-muted-foreground mt-2">
            Please try refreshing the page or contact your estate administrator.
          </p>
        </CardContent>
      </Card>
    );
  }

  const { matter, task_summary } = dashboard;
  const tasks = tasksData?.data ?? [];
  const stakeholders = stakeholdersData?.data ?? [];
  const communications = commsData?.data ?? [];
  const events = eventsData?.data ?? [];

  // Find lead professional
  const leadProfessional = stakeholders.find(
    (s) => s.role === "matter_admin" || s.role === "professional",
  );

  // Distribution notices
  const distributionNotices = communications.filter(
    (c) => c.type === "distribution_notice",
  );

  return (
    <div className="space-y-8">
      {/* Hero header */}
      <div className="text-center space-y-2 pt-2 pb-4">
        <h1 className="text-2xl sm:text-3xl font-serif font-semibold text-foreground tracking-tight">
          Estate of {matter.decedent_name}
        </h1>
        <p className="text-muted-foreground text-sm">
          We are working to settle this estate as smoothly as possible.
        </p>
      </div>

      {/* Phase progress */}
      <PhaseProgress
        currentPhase={matter.phase}
        completionPercentage={task_summary.completion_percentage}
      />

      {/* Info cards */}
      <InfoCards
        completionPercentage={task_summary.completion_percentage}
        leadProfessional={leadProfessional ?? null}
      />

      {/* Milestone timeline */}
      <MilestoneTimeline
        tasks={tasks}
        events={events}
        matter={matter}
      />

      {/* Distribution summary */}
      {distributionNotices.length > 0 && (
        <DistributionSummary
          communications={distributionNotices}
          matterId={matterId}
        />
      )}
    </div>
  );
}
