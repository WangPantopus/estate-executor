"use client";

import { use, useState, useCallback, useRef, useEffect, useMemo } from "react";
import { Download, Loader2, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import { useApi, useStakeholders } from "@/hooks";
import type { EventResponse, CursorPaginatedResponse } from "@/lib/types";
import { TooltipProvider } from "@/components/ui/tooltip";

import {
  ActivityFilterBar,
  type ActivityFilterState,
  EMPTY_ACTIVITY_FILTERS,
  hasActiveFilters,
} from "./_components/ActivityFilterBar";
import { EventTimeline } from "./_components/EventTimeline";
import { describeEvent, formatChanges } from "./_components/eventDescription";

// ─── Constants ────────────────────────────────────────────────────────────────

const FIRM_ID = "current";
const PAGE_SIZE = 50;

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ActivityPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);
  const api = useApi();

  // ─── Data ───────────────────────────────────────────────────────────────────
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);
  const stakeholders = stakeholdersData?.data ?? [];

  const [events, setEvents] = useState<EventResponse[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(false);

  // ─── UI state ───────────────────────────────────────────────────────────────
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<ActivityFilterState>(EMPTY_ACTIVITY_FILTERS);
  const [exporting, setExporting] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // ─── Fetch events ───────────────────────────────────────────────────────────
  const fetchEvents = useCallback(
    async (cursorVal: string | null, append: boolean) => {
      if (append) setLoadingMore(true);
      else setLoading(true);

      try {
        const params: Record<string, string | number> = { per_page: PAGE_SIZE };
        if (cursorVal) params.cursor = cursorVal;
        if (filters.entityType) params.entity_type = filters.entityType;
        if (filters.action) params.action = filters.action;

        const result: CursorPaginatedResponse<EventResponse> = await api.getEvents(
          FIRM_ID,
          matterId,
          params as any,
        );

        let newEvents = result.data;

        // Client-side filtering for actor and date (not supported by API filters)
        if (filters.actorId) {
          if (filters.actorId === "__system__") {
            newEvents = newEvents.filter((e) => e.actor_type === "system");
          } else if (filters.actorId === "__ai__") {
            newEvents = newEvents.filter((e) => e.actor_type === "ai");
          } else {
            newEvents = newEvents.filter((e) => e.actor_id === filters.actorId);
          }
        }
        if (filters.dateFrom) {
          newEvents = newEvents.filter((e) => e.created_at >= filters.dateFrom);
        }
        if (filters.dateTo) {
          const toEnd = filters.dateTo + "T23:59:59";
          newEvents = newEvents.filter((e) => e.created_at <= toEnd);
        }

        setEvents((prev) => (append ? [...prev, ...newEvents] : newEvents));
        setCursor(result.meta.next_cursor);
        setHasMore(result.meta.has_more);
        setError(false);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [api, matterId, filters],
  );

  // Initial load and reload on filter change
  useEffect(() => {
    setEvents([]);
    setCursor(null);
    setHasMore(true);
    fetchEvents(null, false);
  }, [fetchEvents]);

  // Infinite scroll
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !loading) {
          fetchEvents(cursor, true);
        }
      },
      { rootMargin: "200px" },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadingMore, loading, cursor, fetchEvents]);

  // ─── CSV export ─────────────────────────────────────────────────────────────
  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      // Fetch all events for export
      let allEvents: EventResponse[] = [];
      let exportCursor: string | null = null;
      let more = true;

      let iterations = 0;
      while (more && iterations < 50) {
        iterations++;
        const params: Record<string, string | number> = { per_page: 200 };
        if (exportCursor) params.cursor = exportCursor;
        if (filters.entityType) params.entity_type = filters.entityType;
        if (filters.action) params.action = filters.action;

        const result: CursorPaginatedResponse<EventResponse> = await api.getEvents(
          FIRM_ID,
          matterId,
          params as any,
        );

        allEvents = [...allEvents, ...result.data];
        const prevCursor: string | null = exportCursor;
        exportCursor = result.meta.next_cursor;
        more = result.meta.has_more;

        // Guard against non-advancing cursor or safety limit
        if (allEvents.length >= 5000) break;
        if (exportCursor === prevCursor) break;
      }

      // Generate CSV
      const headers = ["Timestamp", "Actor", "Actor Type", "Entity Type", "Action", "Description", "Changes"];
      const rows = allEvents.map((e) => {
        const changes = formatChanges(e.changes);
        const changesStr = changes
          .map((c) => `${c.field}: ${c.from} → ${c.to}`)
          .join("; ");
        return [
          new Date(e.created_at).toISOString(),
          e.actor_name ?? e.actor_type,
          e.actor_type,
          e.entity_type,
          e.action,
          describeEvent(e),
          changesStr,
        ];
      });

      const csvContent = [
        headers.join(","),
        ...rows.map((row) =>
          row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","),
        ),
      ].join("\n");

      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `activity-log-${matterId}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      // Silent fail
    } finally {
      setExporting(false);
    }
  }, [api, matterId, filters]);

  // ─── Render ─────────────────────────────────────────────────────────────────
  if (loading && events.length === 0) {
    return (
      <div className="space-y-4">
        <PageHeader title="Activity Log" />
        <LoadingState variant="list" />
      </div>
    );
  }

  if (error && events.length === 0) {
    return (
      <div className="space-y-4">
        <PageHeader title="Activity Log" />
        <div className="py-12 text-center">
          <p className="text-danger">Failed to load activity log.</p>
          <p className="text-sm text-muted-foreground mt-1">
            Please try refreshing the page.
          </p>
        </div>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* Header */}
        <PageHeader
          title="Activity Log"
          actions={
            <div className="flex items-center gap-2">
              <Button
                variant={showFilters ? "outline" : "ghost"}
                size="sm"
                onClick={() => setShowFilters((v) => !v)}
              >
                <Filter className="size-4 mr-1" />
                Filters
                {hasActiveFilters(filters) && (
                  <span className="ml-1 size-2 rounded-full bg-primary inline-block" />
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                disabled={exporting}
              >
                {exporting ? (
                  <Loader2 className="size-4 mr-1 animate-spin" />
                ) : (
                  <Download className="size-4 mr-1" />
                )}
                Export CSV
              </Button>
            </div>
          }
        />

        {/* Filters */}
        {showFilters && (
          <ActivityFilterBar
            filters={filters}
            onChange={setFilters}
            stakeholders={stakeholders}
          />
        )}

        {/* Event count */}
        <p className="text-xs text-muted-foreground">
          {events.length} event{events.length !== 1 ? "s" : ""} loaded
          {hasMore && " (scroll for more)"}
        </p>

        {/* Timeline */}
        <EventTimeline events={events} />

        {/* Infinite scroll sentinel */}
        <div ref={sentinelRef} className="h-1" />

        {/* Loading more indicator */}
        {loadingMore && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="size-5 text-primary animate-spin" />
            <span className="ml-2 text-sm text-muted-foreground">Loading more...</span>
          </div>
        )}

        {/* End of list */}
        {!hasMore && events.length > 0 && (
          <p className="text-xs text-muted-foreground text-center py-4">
            End of activity log
          </p>
        )}
      </div>
    </TooltipProvider>
  );
}
