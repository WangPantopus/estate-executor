"use client";

import Link from "next/link";
import { AlertTriangle, Clock, Flag, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PortfolioMatterItem } from "@/lib/types";

interface Props {
  items: PortfolioMatterItem[];
}

interface RiskFlag {
  matterId: string;
  matterTitle: string;
  decedentName: string;
  type: "overdue" | "dispute" | "blocked" | "deadline";
  label: string;
  detail: string;
  href: string;
  severity: "red" | "amber";
}

function extractFlags(items: PortfolioMatterItem[]): RiskFlag[] {
  const flags: RiskFlag[] = [];

  for (const item of items) {
    const m = item.matter;

    if (item.overdue_task_count > 0) {
      flags.push({
        matterId: m.id,
        matterTitle: m.title,
        decedentName: m.decedent_name,
        type: "overdue",
        label: `${item.overdue_task_count} overdue task${item.overdue_task_count > 1 ? "s" : ""}`,
        detail: m.title,
        href: `/matters/${m.id}/tasks?status=overdue`,
        severity: "red",
      });
    }

    if (item.has_dispute) {
      flags.push({
        matterId: m.id,
        matterTitle: m.title,
        decedentName: m.decedent_name,
        type: "dispute",
        label: "Unresolved dispute",
        detail: m.title,
        href: `/matters/${m.id}/communications`,
        severity: "red",
      });
    }

    if (item.oldest_blocked_task_days != null && item.oldest_blocked_task_days > 7) {
      flags.push({
        matterId: m.id,
        matterTitle: m.title,
        decedentName: m.decedent_name,
        type: "blocked",
        label: `Task blocked ${item.oldest_blocked_task_days} days`,
        detail: m.title,
        href: `/matters/${m.id}/tasks?status=blocked`,
        severity: item.oldest_blocked_task_days > 14 ? "red" : "amber",
      });
    }
  }

  // Sort by severity (red first)
  flags.sort((a, b) => (a.severity === "red" ? -1 : 1) - (b.severity === "red" ? -1 : 1));

  return flags;
}

const iconMap = {
  overdue: AlertTriangle,
  dispute: ShieldAlert,
  blocked: Clock,
  deadline: Flag,
};

export function RiskFlagsPanel({ items }: Props) {
  const flags = extractFlags(items);

  if (flags.length === 0) {
    return (
      <Card>
        <CardContent className="py-6 text-center">
          <div className="flex flex-col items-center gap-2">
            <div className="flex size-10 items-center justify-center rounded-full bg-success/10">
              <AlertTriangle className="size-5 text-success" />
            </div>
            <p className="text-sm font-medium text-foreground">All matters on track</p>
            <p className="text-xs text-muted-foreground">No risk flags across your portfolio</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertTriangle className="size-4 text-danger" />
          Risk Flags
          <Badge variant="danger" className="ml-1">
            {flags.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {flags.slice(0, 8).map((flag, i) => {
          const Icon = iconMap[flag.type];
          return (
            <Link
              key={`${flag.matterId}-${flag.type}-${i}`}
              href={flag.href}
              className="flex items-center gap-3 rounded-lg border border-border px-3 py-2.5 hover:bg-surface-elevated/50 transition-colors group"
            >
              <div
                className={`flex size-8 items-center justify-center rounded-md ${
                  flag.severity === "red"
                    ? "bg-danger/10 text-danger"
                    : "bg-warning/10 text-warning"
                }`}
              >
                <Icon className="size-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {flag.label}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {flag.detail}
                </p>
              </div>
              <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                View
              </span>
            </Link>
          );
        })}
        {flags.length > 8 && (
          <p className="text-xs text-muted-foreground text-center pt-1">
            +{flags.length - 8} more flags
          </p>
        )}
      </CardContent>
    </Card>
  );
}
