import {
  CheckCircle2,
  AlertTriangle,
  Calendar,
  DollarSign,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { TaskSummary, AssetSummary, DeadlineResponse } from "@/lib/types";

interface MetricsRowProps {
  taskSummary: TaskSummary;
  assetSummary: AssetSummary;
  upcomingDeadlines: DeadlineResponse[];
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr);
  const now = new Date();
  return Math.ceil(
    (target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24),
  );
}

export function MetricsRow({
  taskSummary,
  assetSummary,
  upcomingDeadlines,
}: MetricsRowProps) {
  const nextDeadline = upcomingDeadlines[0];
  const nextDays = nextDeadline ? daysUntil(nextDeadline.due_date) : null;
  const completedTasks = taskSummary.complete + taskSummary.waived;
  const percentage = taskSummary.total
    ? Math.round((completedTasks / taskSummary.total) * 100)
    : 0;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* Total Tasks */}
      <Card>
        <CardContent className="flex items-center gap-4 pt-6">
          <CircularProgress value={percentage} />
          <div>
            <p className="text-sm text-muted-foreground">Tasks</p>
            <p className="text-lg font-medium">
              {completedTasks}{" "}
              <span className="text-muted-foreground font-normal">
                / {taskSummary.total}
              </span>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Overdue Items */}
      <Card>
        <CardContent className="flex items-center gap-4 pt-6">
          <div
            className={`flex size-10 items-center justify-center rounded-full ${
              taskSummary.overdue > 0
                ? "bg-danger-light text-danger"
                : "bg-success-light text-success"
            }`}
          >
            {taskSummary.overdue > 0 ? (
              <AlertTriangle className="size-5" />
            ) : (
              <CheckCircle2 className="size-5" />
            )}
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Overdue</p>
            <p className="text-lg font-medium">
              {taskSummary.overdue > 0 ? (
                <span className="text-danger">{taskSummary.overdue} items</span>
              ) : (
                <span className="text-success">All clear</span>
              )}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Next Deadline */}
      <Card>
        <CardContent className="flex items-center gap-4 pt-6">
          <div
            className={`flex size-10 items-center justify-center rounded-full ${
              nextDays !== null && nextDays < 3
                ? "bg-danger-light text-danger"
                : nextDays !== null && nextDays < 7
                  ? "bg-warning-light text-warning"
                  : "bg-info-light text-info"
            }`}
          >
            <Calendar className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm text-muted-foreground">Next Deadline</p>
            {nextDeadline ? (
              <>
                <p className="text-sm font-medium truncate">
                  {nextDeadline.title}
                </p>
                <p
                  className={`text-xs ${
                    nextDays !== null && nextDays < 3
                      ? "text-danger"
                      : nextDays !== null && nextDays < 7
                        ? "text-warning"
                        : "text-muted-foreground"
                  }`}
                >
                  {nextDays !== null && nextDays < 0
                    ? `${Math.abs(nextDays)}d overdue`
                    : nextDays === 0
                      ? "Due today"
                      : `${nextDays}d remaining`}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">None upcoming</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Estate Value */}
      <Card>
        <CardContent className="flex items-center gap-4 pt-6">
          <div className="flex size-10 items-center justify-center rounded-full bg-gold/10 text-gold">
            <DollarSign className="size-5" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Est. Value</p>
            <p className="text-lg font-medium">
              {assetSummary.total_estimated_value
                ? `$${assetSummary.total_estimated_value.toLocaleString()}`
                : "—"}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Circular progress ───────────────────────────────────────────────────────

function CircularProgress({ value }: { value: number }) {
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative size-10">
      <svg className="size-10 -rotate-90" viewBox="0 0 40 40">
        <circle
          cx="20"
          cy="20"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          className="text-surface-elevated"
        />
        <circle
          cx="20"
          cy="20"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="text-primary transition-all duration-500"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[10px] font-medium">
        {value}%
      </span>
    </div>
  );
}
