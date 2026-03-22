"use client";

import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ENTITY_TYPE_LABELS, FUNDING_STATUS_LABELS } from "@/lib/constants";
import type { Entity, FundingStatus } from "@/lib/types";

const FUNDING_VARIANT: Record<FundingStatus, "success" | "warning" | "danger" | "muted"> = {
  fully_funded: "success",
  partially_funded: "warning",
  unfunded: "danger",
  unknown: "muted",
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

interface EntityListTableProps {
  entities: Entity[];
  onEntityClick: (entityId: string) => void;
}

export function EntityListTable({ entities, onEntityClick }: EntityListTableProps) {
  if (entities.length === 0) return null;

  return (
    <div className="rounded-lg border border-border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead className="hidden sm:table-cell">Trustee</TableHead>
            <TableHead className="hidden md:table-cell">Successor Trustee</TableHead>
            <TableHead>Funding</TableHead>
            <TableHead className="text-right">Assets</TableHead>
            <TableHead className="text-right">Total Value</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entities.map((entity) => {
            const totalValue = entity.assets.reduce(
              (sum, a) => sum + (a.current_estimated_value ?? 0),
              0,
            );
            return (
              <TableRow
                key={entity.id}
                className="cursor-pointer"
                onClick={() => onEntityClick(entity.id)}
              >
                <TableCell className="font-medium">{entity.name}</TableCell>
                <TableCell className="text-muted-foreground text-xs">
                  {ENTITY_TYPE_LABELS[entity.entity_type]}
                </TableCell>
                <TableCell className="hidden sm:table-cell text-muted-foreground">
                  {entity.trustee ?? "—"}
                </TableCell>
                <TableCell className="hidden md:table-cell text-muted-foreground">
                  {entity.successor_trustee ?? "—"}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={FUNDING_VARIANT[entity.funding_status]}
                    className="text-[10px]"
                  >
                    {FUNDING_STATUS_LABELS[entity.funding_status]}
                  </Badge>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {entity.assets.length}
                </TableCell>
                <TableCell className="text-right tabular-nums font-medium">
                  {totalValue > 0 ? formatCurrency(totalValue) : "—"}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
