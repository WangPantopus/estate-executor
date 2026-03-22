"use client";

import { Badge } from "@/components/ui/badge";
import { ASSET_STATUS_LABELS, ASSET_STATUS_ORDER } from "@/lib/constants";
import type { AssetListItem, AssetStatus } from "@/lib/types";

const STATUS_VARIANT: Record<AssetStatus, "info" | "gold" | "warning" | "success"> = {
  discovered: "info",
  valued: "gold",
  transferred: "warning",
  distributed: "success",
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

interface AssetSummaryBarProps {
  assets: AssetListItem[];
}

export function AssetSummaryBar({ assets }: AssetSummaryBarProps) {
  const totalValue = assets.reduce(
    (sum, a) => sum + (a.current_estimated_value ?? a.date_of_death_value ?? 0),
    0,
  );

  const countByStatus = ASSET_STATUS_ORDER.reduce(
    (acc, status) => {
      acc[status] = assets.filter((a) => a.status === status).length;
      return acc;
    },
    {} as Record<AssetStatus, number>,
  );

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Total value */}
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Total Estimated Value
          </p>
          <p className="text-2xl font-semibold text-foreground tracking-tight mt-0.5">
            {formatCurrency(totalValue)}
          </p>
        </div>

        {/* Status counts */}
        <div className="flex items-center gap-2 flex-wrap">
          {ASSET_STATUS_ORDER.map((status) => (
            <Badge
              key={status}
              variant={STATUS_VARIANT[status]}
              className="tabular-nums"
            >
              {countByStatus[status]} {ASSET_STATUS_LABELS[status]}
            </Badge>
          ))}
        </div>
      </div>

      <p className="text-xs text-muted-foreground mt-3">
        All values are estimates until final appraisal.
      </p>
    </div>
  );
}
