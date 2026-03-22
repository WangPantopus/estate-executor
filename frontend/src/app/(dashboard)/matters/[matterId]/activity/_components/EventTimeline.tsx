"use client";

import { useState } from "react";
import {
  CheckSquare,
  Package,
  FileText,
  UserPlus,
  Briefcase,
  Clock,
  MessageSquare,
  Building2,
  ChevronDown,
  ChevronRight,
  ArrowRight,
  Bot,
  Settings,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { EventResponse } from "@/lib/types";
import { describeEvent, formatChanges } from "./eventDescription";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const ENTITY_ICONS: Record<string, React.ReactNode> = {
  task: <CheckSquare className="size-4" />,
  asset: <Package className="size-4" />,
  document: <FileText className="size-4" />,
  stakeholder: <UserPlus className="size-4" />,
  matter: <Briefcase className="size-4" />,
  deadline: <Clock className="size-4" />,
  communication: <MessageSquare className="size-4" />,
  entity: <Building2 className="size-4" />,
};

const ENTITY_COLORS: Record<string, string> = {
  task: "text-blue-600 bg-blue-50",
  asset: "text-emerald-600 bg-emerald-50",
  document: "text-violet-600 bg-violet-50",
  stakeholder: "text-amber-600 bg-amber-50",
  matter: "text-slate-600 bg-slate-100",
  deadline: "text-red-600 bg-red-50",
  communication: "text-cyan-600 bg-cyan-50",
  entity: "text-rose-600 bg-rose-50",
};

const ACTOR_ICONS: Record<string, React.ReactNode> = {
  system: <Settings className="size-3" />,
  ai: <Bot className="size-3" />,
};

function relativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay === 1) return "Yesterday";
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function absoluteTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function dateLabel(dateStr: string): string {
  const date = new Date(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const eventDay = new Date(date);
  eventDay.setHours(0, 0, 0, 0);

  const diffDays = Math.round(
    (today.getTime() - eventDay.getTime()) / (1000 * 60 * 60 * 24),
  );

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function eventDateKey(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ─── Change Diff ──────────────────────────────────────────────────────────────

function ChangeDiff({ changes }: { changes: Record<string, unknown> | null }) {
  const diffs = formatChanges(changes);
  if (diffs.length === 0) return null;

  return (
    <div className="mt-2 rounded-md bg-surface-elevated p-2.5 space-y-1.5">
      {diffs.map((diff, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="font-medium text-muted-foreground capitalize min-w-[80px]">
            {diff.field}
          </span>
          <span className="text-muted-foreground line-through">{diff.from}</span>
          <ArrowRight className="size-3 text-muted-foreground shrink-0" />
          <span className="text-foreground font-medium">{diff.to}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Event Row ────────────────────────────────────────────────────────────────

function EventRow({ event }: { event: EventResponse }) {
  const [expanded, setExpanded] = useState(false);
  const hasChanges = event.changes && Object.keys(event.changes).length > 0;
  const description = describeEvent(event);
  const iconColor = ENTITY_COLORS[event.entity_type] ?? "text-gray-500 bg-gray-100";
  const icon = ENTITY_ICONS[event.entity_type] ?? <Settings className="size-4" />;

  return (
    <div className="flex items-start gap-3 py-2.5 group">
      {/* Icon */}
      <div
        className={cn(
          "flex items-center justify-center size-8 rounded-lg shrink-0 mt-0.5",
          iconColor,
        )}
      >
        {icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-foreground">{description}</p>

        {/* Actor + time */}
        <div className="flex items-center gap-2 mt-0.5">
          {event.actor_type !== "user" && (
            <span className="inline-flex items-center gap-0.5 text-xs text-muted-foreground">
              {ACTOR_ICONS[event.actor_type]}
              <span className="capitalize">{event.actor_type}</span>
            </span>
          )}
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="text-xs text-muted-foreground cursor-default">
                {relativeTime(event.created_at)}
              </span>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <p className="text-xs">{absoluteTime(event.created_at)}</p>
            </TooltipContent>
          </Tooltip>
          <Badge variant="muted" className="text-[10px] capitalize">
            {event.entity_type}
          </Badge>
        </div>

        {/* Expandable changes */}
        {hasChanges && (
          <>
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mt-1 transition-colors"
            >
              {expanded ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
              Changes
            </button>
            {expanded && <ChangeDiff changes={event.changes} />}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Timeline ─────────────────────────────────────────────────────────────────

interface EventTimelineProps {
  events: EventResponse[];
}

export function EventTimeline({ events }: EventTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">No events found.</p>
      </div>
    );
  }

  // Group by date
  const groups: { dateKey: string; label: string; events: EventResponse[] }[] = [];
  let currentKey = "";

  for (const event of events) {
    const key = eventDateKey(event.created_at);
    if (key !== currentKey) {
      currentKey = key;
      groups.push({ dateKey: key, label: dateLabel(event.created_at), events: [] });
    }
    groups[groups.length - 1].events.push(event);
  }

  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <div key={group.dateKey}>
          {/* Date separator */}
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {group.label}
            </span>
            <div className="flex-1 h-px bg-border" />
          </div>

          {/* Events */}
          <div className="divide-y divide-border">
            {group.events.map((event) => (
              <EventRow key={event.id} event={event} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
