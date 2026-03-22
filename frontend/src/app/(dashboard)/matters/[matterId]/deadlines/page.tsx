"use client";

import { use, useState, useMemo, useCallback } from "react";
import { Plus, CalendarDays, AlignJustify } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
} from "@/components/ui/sheet";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import { EmptyState } from "@/components/layout/EmptyState";
import { useDeadlines, useStakeholders, useTasks } from "@/hooks";
import type { DeadlineResponse } from "@/lib/types";

import { DeadlineSummaryBar } from "./_components/DeadlineSummaryBar";
import { CalendarView } from "./_components/CalendarView";
import { TimelineView } from "./_components/TimelineView";
import { DeadlineDetailPanel } from "./_components/DeadlineDetailPanel";
import { AddDeadlineDialog } from "./_components/AddDeadlineDialog";

// ─── Constants ────────────────────────────────────────────────────────────────

const FIRM_ID = "current";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function daysUntil(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dateStr + "T00:00:00");
  return Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DeadlinesPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);

  // ─── Data fetching ──────────────────────────────────────────────────────────
  const {
    data: deadlinesData,
    isLoading,
    error,
  } = useDeadlines(FIRM_ID, matterId, { per_page: 200 });
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);
  const { data: tasksData } = useTasks(FIRM_ID, matterId, { per_page: 200 });

  const allDeadlines = deadlinesData?.data ?? [];
  const stakeholders = stakeholdersData?.data ?? [];
  const tasks = tasksData?.data ?? [];

  // ─── UI state ───────────────────────────────────────────────────────────────
  const [viewMode, setViewMode] = useState<"calendar" | "timeline">("calendar");
  const [summaryFilter, setSummaryFilter] = useState<string | null>(null);
  const [detailDeadline, setDetailDeadline] = useState<DeadlineResponse | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  // ─── Filter from summary bar ────────────────────────────────────────────────
  const filteredDeadlines = useMemo(() => {
    if (!summaryFilter) return allDeadlines;

    switch (summaryFilter) {
      case "overdue":
        return allDeadlines.filter(
          (d) => d.status === "upcoming" && daysUntil(d.due_date) < 0,
        );
      case "this_week":
        return allDeadlines.filter(
          (d) =>
            d.status === "upcoming" &&
            daysUntil(d.due_date) >= 0 &&
            daysUntil(d.due_date) <= 7,
        );
      case "this_month":
        return allDeadlines.filter(
          (d) =>
            d.status === "upcoming" &&
            daysUntil(d.due_date) >= 0 &&
            daysUntil(d.due_date) <= 30,
        );
      case "completed":
        return allDeadlines.filter((d) => d.status === "completed");
      default:
        return allDeadlines;
    }
  }, [allDeadlines, summaryFilter]);

  // ─── Handlers ───────────────────────────────────────────────────────────────
  const handleDeadlineClick = useCallback(
    (deadlineId: string) => {
      const dl = allDeadlines.find((d) => d.id === deadlineId);
      if (dl) setDetailDeadline(dl);
    },
    [allDeadlines],
  );

  const handleSummaryFilter = useCallback((filter: string) => {
    setSummaryFilter(filter || null);
  }, []);

  // ─── Render ─────────────────────────────────────────────────────────────────
  if (isLoading) {
    return <LoadingState variant="cards" />;
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-danger">Failed to load deadlines.</p>
        <p className="text-sm text-muted-foreground mt-1">
          Please try refreshing the page.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <PageHeader
        title="Compliance Calendar"
        actions={
          <div className="flex items-center gap-2">
            {/* View toggle */}
            <div className="flex items-center rounded-md border border-border">
              <Button
                variant={viewMode === "calendar" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("calendar")}
                className="rounded-r-none border-0 hidden md:inline-flex"
              >
                <CalendarDays className="size-4 mr-1" />
                Calendar
              </Button>
              <Button
                variant={viewMode === "timeline" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("timeline")}
                className="rounded-l-none border-0 md:rounded-l-none"
              >
                <AlignJustify className="size-4 mr-1" />
                Timeline
              </Button>
            </div>

            {/* Add deadline */}
            <Button size="sm" onClick={() => setAddDialogOpen(true)}>
              <Plus className="size-4 mr-1" />
              Add Deadline
            </Button>
          </div>
        }
      />

      {/* Summary bar */}
      <DeadlineSummaryBar
        deadlines={allDeadlines}
        onFilter={handleSummaryFilter}
        activeFilter={summaryFilter}
      />

      {/* Filter indicator */}
      {summaryFilter && (
        <div className="flex items-center gap-2">
          <p className="text-xs text-muted-foreground">
            Showing {filteredDeadlines.length} deadline{filteredDeadlines.length !== 1 ? "s" : ""}
          </p>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSummaryFilter(null)}
            className="text-xs h-6"
          >
            Clear filter
          </Button>
        </div>
      )}

      {/* Content */}
      {allDeadlines.length === 0 ? (
        <EmptyState
          title="No deadlines"
          description="Deadlines are auto-generated when a matter is created, or you can add them manually."
          action={
            <Button size="sm" onClick={() => setAddDialogOpen(true)}>
              <Plus className="size-4 mr-1" />
              Add Deadline
            </Button>
          }
        />
      ) : viewMode === "calendar" ? (
        <CalendarView
          deadlines={filteredDeadlines}
          onDeadlineClick={handleDeadlineClick}
        />
      ) : (
        <TimelineView
          deadlines={filteredDeadlines}
          onDeadlineClick={handleDeadlineClick}
        />
      )}

      {/* Deadline detail side panel */}
      <Sheet
        open={!!detailDeadline}
        onOpenChange={(open) => {
          if (!open) setDetailDeadline(null);
        }}
      >
        <SheetContent side="right" className="w-full sm:max-w-lg p-0">
          {detailDeadline && (
            <DeadlineDetailPanel
              deadline={detailDeadline}
              firmId={FIRM_ID}
              matterId={matterId}
              stakeholders={stakeholders}
              onClose={() => setDetailDeadline(null)}
            />
          )}
        </SheetContent>
      </Sheet>

      {/* Add deadline dialog */}
      <AddDeadlineDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        firmId={FIRM_ID}
        matterId={matterId}
        stakeholders={stakeholders}
        tasks={tasks}
      />
    </div>
  );
}
