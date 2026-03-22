import Link from "next/link";
import {
  FileText,
  CheckSquare,
  UserPlus,
  Landmark,
  MessageSquare,
  Calendar,
  Activity,
  Settings,
  Building2,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { EventResponse } from "@/lib/types";

const ENTITY_ICONS: Record<string, React.ElementType> = {
  task: CheckSquare,
  asset: Landmark,
  document: FileText,
  stakeholder: UserPlus,
  communication: MessageSquare,
  deadline: Calendar,
  entity: Building2,
  matter: Settings,
};

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatAction(event: EventResponse): string {
  const entityType = event.entity_type
    .replace(/_/g, " ");
  return `${event.action.replace(/_/g, " ")} ${entityType}`;
}

interface RecentActivityProps {
  events: EventResponse[];
  matterId: string;
}

export function RecentActivity({ events, matterId }: RecentActivityProps) {
  const displayEvents = events.slice(0, 10);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Recent Activity</CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/matters/${matterId}/activity`}>View all</Link>
        </Button>
      </CardHeader>
      <CardContent className="pt-0">
        {displayEvents.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No activity yet.
          </p>
        ) : (
          <div className="space-y-0">
            {displayEvents.map((event, i) => {
              const Icon =
                ENTITY_ICONS[event.entity_type] ?? Activity;
              return (
                <div key={event.id} className="flex gap-3 py-2.5">
                  <div className="flex flex-col items-center">
                    <div className="flex size-7 items-center justify-center rounded-full bg-surface-elevated text-muted-foreground shrink-0">
                      <Icon className="size-3.5" />
                    </div>
                    {i < displayEvents.length - 1 && (
                      <div className="w-px flex-1 bg-border mt-1" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0 pt-0.5">
                    <p className="text-sm">
                      <span className="font-medium">
                        {event.actor_name ?? "System"}
                      </span>{" "}
                      <span className="text-muted-foreground">
                        {formatAction(event)}
                      </span>
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {formatTimeAgo(event.created_at)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
