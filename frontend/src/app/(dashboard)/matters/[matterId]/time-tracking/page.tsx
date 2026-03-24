"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import {
  Clock,
  Plus,
  Download,
  Trash2,
  DollarSign,
  Timer,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useTimeEntries,
  useTimeSummary,
  useDeleteTimeEntry,
  useTasks,
} from "@/hooks";
import type { TimeEntry } from "@/lib/types";
import { LogTimeDialog } from "./_components/LogTimeDialog";

const FIRM_ID = "current";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function formatDuration(hours: number, minutes: number): string {
  if (hours === 0 && minutes === 0) return "0m";
  if (hours === 0) return `${minutes}m`;
  if (minutes === 0) return `${hours}h`;
  return `${hours}h ${minutes}m`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function TimeTrackingPage() {
  const { matterId } = useParams<{ matterId: string }>();
  const firmId = FIRM_ID;
  const [showLogDialog, setShowLogDialog] = useState(false);
  const [preselectedTaskId, setPreselectedTaskId] = useState<string | null>(
    null
  );

  const { data: entriesData, isLoading: entriesLoading } = useTimeEntries(
    firmId,
    matterId
  );
  const { data: summary } = useTimeSummary(firmId, matterId);
  const { data: tasksData } = useTasks(firmId, matterId);
  const deleteMutation = useDeleteTimeEntry(firmId, matterId);

  const entries = entriesData?.data ?? [];
  const tasks = tasksData?.data ?? [];

  const handleExportCsv = async () => {
    try {
      const res = await fetch(
        `${API_BASE_URL}/firms/${firmId}/matters/${matterId}/time/export?format=csv`,
        { credentials: "include" }
      );
      if (!res.ok) throw new Error("Export failed");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "time-tracking-export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Fallback: open in new tab (works if session cookie auth is enabled)
      window.open(
        `${API_BASE_URL}/firms/${firmId}/matters/${matterId}/time/export?format=csv`,
        "_blank"
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">
            Time Tracking
          </h1>
          <p className="text-sm text-muted-foreground">
            Track time spent on tasks for billing and reporting
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCsv}>
            <Download className="size-4 mr-1" />
            Export CSV
          </Button>
          <Button
            size="sm"
            onClick={() => {
              setPreselectedTaskId(null);
              setShowLogDialog(true);
            }}
          >
            <Plus className="size-4 mr-1" />
            Log Time
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Timer className="size-4" />
                <span className="text-xs font-medium">Total Time</span>
              </div>
              <p className="text-2xl font-semibold tabular-nums">
                {summary.total_decimal_hours}h
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <DollarSign className="size-4" />
                <span className="text-xs font-medium">Billable</span>
              </div>
              <p className="text-2xl font-semibold tabular-nums text-green-600">
                {summary.billable_hours}h
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Clock className="size-4" />
                <span className="text-xs font-medium">Non-Billable</span>
              </div>
              <p className="text-2xl font-semibold tabular-nums text-gray-500">
                {summary.non_billable_hours}h
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Clock className="size-4" />
                <span className="text-xs font-medium">Professionals</span>
              </div>
              <p className="text-2xl font-semibold tabular-nums">
                {summary.by_stakeholder.length}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Time entries table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Time Entries</CardTitle>
        </CardHeader>
        <CardContent>
          {entriesLoading ? (
            <div className="py-8 text-center text-muted-foreground">
              Loading...
            </div>
          ) : entries.length === 0 ? (
            <div className="py-12 text-center">
              <Clock className="size-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-muted-foreground">No time entries yet.</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => setShowLogDialog(true)}
              >
                <Plus className="size-4 mr-1" />
                Log your first entry
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium text-muted-foreground">
                      Date
                    </th>
                    <th className="pb-2 font-medium text-muted-foreground">
                      Professional
                    </th>
                    <th className="pb-2 font-medium text-muted-foreground">
                      Task
                    </th>
                    <th className="pb-2 font-medium text-muted-foreground text-right">
                      Time
                    </th>
                    <th className="pb-2 font-medium text-muted-foreground">
                      Description
                    </th>
                    <th className="pb-2 font-medium text-muted-foreground text-center">
                      Billable
                    </th>
                    <th className="pb-2 w-10" />
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry: TimeEntry) => (
                    <tr
                      key={entry.id}
                      className="group border-b last:border-0 hover:bg-surface-elevated transition-colors"
                    >
                      <td className="py-2.5 pr-3 whitespace-nowrap">
                        {formatDate(entry.entry_date)}
                      </td>
                      <td className="py-2.5 pr-3 truncate max-w-[120px]">
                        {entry.stakeholder_name}
                      </td>
                      <td className="py-2.5 pr-3 truncate max-w-[180px] text-muted-foreground">
                        {entry.task_title || "—"}
                      </td>
                      <td className="py-2.5 pr-3 text-right font-medium tabular-nums whitespace-nowrap">
                        {formatDuration(entry.hours, entry.minutes)}
                      </td>
                      <td className="py-2.5 pr-3 truncate max-w-[200px]">
                        {entry.description}
                      </td>
                      <td className="py-2.5 text-center">
                        {entry.billable ? (
                          <span className="inline-block size-2 rounded-full bg-green-500" />
                        ) : (
                          <span className="inline-block size-2 rounded-full bg-gray-300" />
                        )}
                      </td>
                      <td className="py-2.5">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-7 opacity-0 group-hover:opacity-100"
                          onClick={() => deleteMutation.mutate(entry.id)}
                        >
                          <Trash2 className="size-3.5 text-danger" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* By Professional breakdown */}
      {summary && summary.by_stakeholder.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">
              By Professional
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {summary.by_stakeholder.map((s) => (
                <div
                  key={s.stakeholder_id}
                  className="flex items-center justify-between"
                >
                  <span className="text-sm">{s.name}</span>
                  <span className="text-sm font-medium tabular-nums">
                    {s.decimal_hours}h
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Log Time Dialog */}
      <LogTimeDialog
        key={preselectedTaskId ?? "none"}
        open={showLogDialog}
        onOpenChange={setShowLogDialog}
        firmId={firmId}
        matterId={matterId}
        tasks={tasks}
        preselectedTaskId={preselectedTaskId}
      />
    </div>
  );
}
