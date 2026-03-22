import Link from "next/link";
import { Calendar } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { DeadlineResponse } from "@/lib/types";

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr);
  const now = new Date();
  return Math.ceil(
    (target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24),
  );
}

function urgencyColor(days: number): string {
  if (days < 0) return "text-danger";
  if (days < 3) return "text-danger";
  if (days < 7) return "text-warning";
  if (days <= 30) return "text-warning";
  return "text-success";
}

function urgencyDotColor(days: number): string {
  if (days < 0) return "bg-danger";
  if (days < 3) return "bg-danger";
  if (days < 7) return "bg-warning";
  if (days <= 30) return "bg-warning";
  return "bg-success";
}

interface UpcomingDeadlinesCardProps {
  deadlines: DeadlineResponse[];
  matterId: string;
}

export function UpcomingDeadlinesCard({
  deadlines,
  matterId,
}: UpcomingDeadlinesCardProps) {
  const display = deadlines.slice(0, 5);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Upcoming Deadlines</CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/matters/${matterId}/deadlines`}>View calendar</Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-1 pt-0">
        {display.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-2">
            No upcoming deadlines.
          </p>
        ) : (
          display.map((deadline) => {
            const days = daysUntil(deadline.due_date);
            return (
              <div
                key={deadline.id}
                className="flex items-start gap-3 rounded-md px-2 py-2"
              >
                <div
                  className={`mt-1.5 size-2 rounded-full shrink-0 ${urgencyDotColor(days)}`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {deadline.title}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-muted-foreground">
                      {new Date(deadline.due_date).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                    {deadline.assignee_name && (
                      <span className="text-xs text-muted-foreground">
                        · {deadline.assignee_name}
                      </span>
                    )}
                  </div>
                </div>
                <span
                  className={`text-xs font-medium shrink-0 ${urgencyColor(days)}`}
                >
                  {days < 0
                    ? `${Math.abs(days)}d overdue`
                    : days === 0
                      ? "Today"
                      : `${days}d`}
                </span>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
