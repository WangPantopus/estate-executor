"use client";

import { Briefcase, AlertTriangle, Calendar, BarChart3 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { PHASE_LABELS } from "@/lib/constants";
import type { PortfolioSummary } from "@/lib/types";

interface Props {
  summary: PortfolioSummary;
}

export function PortfolioSummaryBar({ summary }: Props) {
  const phaseEntries = Object.entries(summary.matters_by_phase);
  const maxPhaseCount = Math.max(...phaseEntries.map(([, v]) => v), 1);

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* Active Matters */}
      <Card>
        <CardContent className="flex items-center gap-4 py-4">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Briefcase className="size-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">
              {summary.total_active_matters}
            </p>
            <p className="text-xs text-muted-foreground">Active Matters</p>
          </div>
        </CardContent>
      </Card>

      {/* Overdue Tasks */}
      <Card>
        <CardContent className="flex items-center gap-4 py-4">
          <div className={`flex size-10 items-center justify-center rounded-lg ${
            summary.total_overdue_tasks > 0
              ? "bg-danger/10 text-danger"
              : "bg-success/10 text-success"
          }`}>
            <AlertTriangle className="size-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">
              {summary.total_overdue_tasks}
            </p>
            <p className="text-xs text-muted-foreground">Overdue Tasks</p>
          </div>
        </CardContent>
      </Card>

      {/* Deadlines This Week */}
      <Card>
        <CardContent className="flex items-center gap-4 py-4">
          <div className={`flex size-10 items-center justify-center rounded-lg ${
            summary.approaching_deadlines_this_week > 0
              ? "bg-warning/10 text-warning"
              : "bg-muted text-muted-foreground"
          }`}>
            <Calendar className="size-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">
              {summary.approaching_deadlines_this_week}
            </p>
            <p className="text-xs text-muted-foreground">Deadlines This Week</p>
          </div>
        </CardContent>
      </Card>

      {/* Phase Distribution */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="size-4 text-muted-foreground" />
            <p className="text-xs font-medium text-muted-foreground">By Phase</p>
          </div>
          <div className="space-y-1.5">
            {phaseEntries.length === 0 ? (
              <p className="text-xs text-muted-foreground">No active matters</p>
            ) : (
              phaseEntries.map(([phase, count]) => (
                <div key={phase} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-24 truncate">
                    {PHASE_LABELS[phase] ?? phase}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary/70 transition-all"
                      style={{ width: `${(count / maxPhaseCount) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium w-4 text-right">{count}</span>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
