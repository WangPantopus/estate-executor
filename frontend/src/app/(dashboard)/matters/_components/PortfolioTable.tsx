"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ESTATE_TYPE_LABELS, PHASE_LABELS, US_STATES } from "@/lib/constants";
import type { PortfolioMatterItem, RiskLevel } from "@/lib/types";

interface Props {
  items: PortfolioMatterItem[];
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function getStateLabel(code: string): string {
  return US_STATES.find((s) => s.value === code)?.label ?? code;
}

function RiskIndicator({ level }: { level: RiskLevel }) {
  const config = {
    green: { color: "bg-success", label: "On Track" },
    amber: { color: "bg-warning", label: "Attention" },
    red: { color: "bg-danger", label: "Critical" },
  };
  const { color, label } = config[level];

  return (
    <div className="flex items-center gap-1.5" title={label}>
      <span className={`size-2 rounded-full ${color}`} />
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

export function PortfolioTable({ items }: Props) {
  const router = useRouter();

  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Status</TableHead>
            <TableHead>Matter</TableHead>
            <TableHead>Phase</TableHead>
            <TableHead>Progress</TableHead>
            <TableHead className="text-center">Overdue</TableHead>
            <TableHead>Next Deadline</TableHead>
            <TableHead>Jurisdiction</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => {
            const m = item.matter;
            const completion =
              item.total_task_count > 0
                ? Math.round(
                    (item.complete_task_count / item.total_task_count) * 100,
                  )
                : 0;
            const estateLabel =
              ESTATE_TYPE_LABELS[m.estate_type]?.label ?? m.estate_type;

            return (
              <TableRow
                key={m.id}
                className="cursor-pointer"
                onClick={() => router.push(`/matters/${m.id}`)}
              >
                {/* Risk indicator */}
                <TableCell>
                  <RiskIndicator level={item.risk_level} />
                </TableCell>

                {/* Matter info */}
                <TableCell>
                  <Link
                    href={`/matters/${m.id}`}
                    className="font-medium text-foreground hover:text-primary transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {m.title}
                  </Link>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {m.decedent_name} · {estateLabel}
                  </p>
                </TableCell>

                {/* Phase */}
                <TableCell>
                  <Badge variant="muted">
                    {PHASE_LABELS[m.phase] ?? m.phase}
                  </Badge>
                </TableCell>

                {/* Progress bar */}
                <TableCell>
                  <div className="flex items-center gap-2 min-w-[120px]">
                    <Progress value={completion} className="h-1.5 flex-1" />
                    <span className="text-xs text-muted-foreground whitespace-nowrap w-8 text-right">
                      {completion}%
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {item.complete_task_count}/{item.total_task_count} tasks
                  </p>
                </TableCell>

                {/* Overdue count */}
                <TableCell className="text-center">
                  {item.overdue_task_count > 0 ? (
                    <Badge variant="destructive" className="font-mono">
                      {item.overdue_task_count}
                    </Badge>
                  ) : (
                    <span className="text-xs text-muted-foreground">0</span>
                  )}
                </TableCell>

                {/* Next deadline */}
                <TableCell>
                  {item.next_deadline ? (
                    <div>
                      <p className="text-sm">{formatDate(item.next_deadline)}</p>
                      {item.approaching_deadline_count > 0 && (
                        <p className="text-[11px] text-warning">
                          {item.approaching_deadline_count} this week
                        </p>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>

                {/* Jurisdiction */}
                <TableCell className="text-sm text-muted-foreground">
                  {getStateLabel(m.jurisdiction_state)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Card>
  );
}
