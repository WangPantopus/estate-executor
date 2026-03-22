import Link from "next/link";
import { AlertTriangle, Clock, Flag } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { TaskSummary, DeadlineResponse } from "@/lib/types";

interface AlertsPanelProps {
  taskSummary: TaskSummary;
  upcomingDeadlines: DeadlineResponse[];
  matterId: string;
}

export function AlertsPanel({
  taskSummary,
  upcomingDeadlines,
  matterId,
}: AlertsPanelProps) {
  const alerts: {
    icon: React.ElementType;
    message: string;
    href: string;
    severity: "danger" | "warning";
  }[] = [];

  // Overdue tasks
  if (taskSummary.overdue > 0) {
    alerts.push({
      icon: AlertTriangle,
      message: `${taskSummary.overdue} overdue ${taskSummary.overdue === 1 ? "task" : "tasks"} need attention`,
      href: `/matters/${matterId}/tasks?status=overdue`,
      severity: "danger",
    });
  }

  // Missed deadlines
  const missedDeadlines = upcomingDeadlines.filter(
    (d) => d.status === "missed" || new Date(d.due_date) < new Date(),
  );
  if (missedDeadlines.length > 0) {
    alerts.push({
      icon: Clock,
      message: `${missedDeadlines.length} missed ${missedDeadlines.length === 1 ? "deadline" : "deadlines"}`,
      href: `/matters/${matterId}/deadlines`,
      severity: "danger",
    });
  }

  // Blocked tasks
  if (taskSummary.blocked > 0) {
    alerts.push({
      icon: Flag,
      message: `${taskSummary.blocked} ${taskSummary.blocked === 1 ? "task is" : "tasks are"} blocked`,
      href: `/matters/${matterId}/tasks?status=blocked`,
      severity: "warning",
    });
  }

  if (alerts.length === 0) return null;

  return (
    <Card className="border-warning/30 bg-warning-light/30">
      <CardContent className="py-3 space-y-1">
        {alerts.map((alert, i) => (
          <Link
            key={i}
            href={alert.href}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors hover:bg-warning-light/50"
          >
            <alert.icon
              className={`size-4 shrink-0 ${
                alert.severity === "danger" ? "text-danger" : "text-warning"
              }`}
            />
            <span className="text-foreground">{alert.message}</span>
            <span className="ml-auto text-xs text-muted-foreground">
              View →
            </span>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
