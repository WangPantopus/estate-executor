import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type TaskStatus =
  | "not_started"
  | "in_progress"
  | "blocked"
  | "complete"
  | "waived"
  | "cancelled"
  | "overdue";

type AssetStatus = "discovered" | "valued" | "transferred" | "distributed";

type DeadlineStatus = "upcoming" | "completed" | "extended" | "missed";

type InviteStatus = "pending" | "accepted" | "revoked";

type MatterStatus = "active" | "on_hold" | "closed" | "archived";

type StatusType =
  | TaskStatus
  | AssetStatus
  | DeadlineStatus
  | InviteStatus
  | MatterStatus;

const statusConfig: Record<
  StatusType,
  { label: string; variant: "default" | "secondary" | "outline" | "success" | "warning" | "danger" | "info" | "gold" | "muted" }
> = {
  // Task statuses
  not_started: { label: "Not Started", variant: "muted" },
  in_progress: { label: "In Progress", variant: "info" },
  blocked: { label: "Blocked", variant: "warning" },
  complete: { label: "Complete", variant: "success" },
  waived: { label: "Waived", variant: "muted" },
  cancelled: { label: "Cancelled", variant: "muted" },
  overdue: { label: "Overdue", variant: "danger" },

  // Asset statuses
  discovered: { label: "Discovered", variant: "info" },
  valued: { label: "Valued", variant: "gold" },
  transferred: { label: "Transferred", variant: "warning" },
  distributed: { label: "Distributed", variant: "success" },

  // Deadline statuses
  upcoming: { label: "Upcoming", variant: "info" },
  completed: { label: "Completed", variant: "success" },
  extended: { label: "Extended", variant: "warning" },
  missed: { label: "Missed", variant: "danger" },

  // Invite statuses
  pending: { label: "Pending", variant: "warning" },
  accepted: { label: "Accepted", variant: "success" },
  revoked: { label: "Revoked", variant: "muted" },

  // Matter statuses
  active: { label: "Active", variant: "success" },
  on_hold: { label: "On Hold", variant: "warning" },
  closed: { label: "Closed", variant: "muted" },
  archived: { label: "Archived", variant: "muted" },
};

interface StatusBadgeProps {
  status: StatusType;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];

  if (!config) {
    return (
      <Badge variant="muted" className={className}>
        {status}
      </Badge>
    );
  }

  return (
    <Badge variant={config.variant} className={cn("capitalize", className)}>
      {config.label}
    </Badge>
  );
}

export type { TaskStatus, AssetStatus, DeadlineStatus, InviteStatus, MatterStatus, StatusType };
