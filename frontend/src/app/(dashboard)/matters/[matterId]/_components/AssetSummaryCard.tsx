import Link from "next/link";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ASSET_TYPE_LABELS } from "@/lib/constants";
import type { AssetSummary, AssetType } from "@/lib/types";

const STATUS_COLORS: Record<string, { bg: string; label: string }> = {
  discovered: { bg: "bg-info", label: "Discovered" },
  valued: { bg: "bg-gold", label: "Valued" },
  transferred: { bg: "bg-warning", label: "Transferred" },
  distributed: { bg: "bg-success", label: "Distributed" },
};

interface AssetSummaryCardProps {
  assetSummary: AssetSummary;
  matterId: string;
}

export function AssetSummaryCard({
  assetSummary,
  matterId,
}: AssetSummaryCardProps) {
  const { total_count, total_estimated_value, by_type, by_status } =
    assetSummary;
  const statusTotal = Object.values(by_status).reduce((a, b) => a + b, 0);

  // Sort types by count descending
  const typeEntries = Object.entries(by_type)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Assets</CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/matters/${matterId}/assets`}>View all</Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        {/* Total value */}
        <div>
          <p className="text-2xl font-medium tracking-tight">
            {total_estimated_value
              ? `$${total_estimated_value.toLocaleString()}`
              : "—"}
          </p>
          <p className="text-xs text-muted-foreground">
            {total_count} {total_count === 1 ? "asset" : "assets"} total
          </p>
        </div>

        {/* Status progress bar */}
        {statusTotal > 0 && (
          <div className="space-y-2">
            <div className="flex h-2 overflow-hidden rounded-full">
              {Object.entries(STATUS_COLORS).map(([key, { bg }]) => {
                const count = by_status[key] ?? 0;
                if (count === 0) return null;
                return (
                  <div
                    key={key}
                    className={`${bg} transition-all duration-300`}
                    style={{ width: `${(count / statusTotal) * 100}%` }}
                  />
                );
              })}
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {Object.entries(STATUS_COLORS).map(([key, { bg, label }]) => {
                const count = by_status[key] ?? 0;
                if (count === 0) return null;
                return (
                  <div key={key} className="flex items-center gap-1.5">
                    <div className={`size-2 rounded-full ${bg}`} />
                    <span className="text-xs text-muted-foreground">
                      {label} ({count})
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* By type breakdown */}
        {typeEntries.length > 0 && (
          <div className="space-y-1.5 pt-1">
            {typeEntries.map(([type, count]) => (
              <div
                key={type}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-muted-foreground truncate">
                  {ASSET_TYPE_LABELS[type as AssetType] ?? type}
                </span>
                <span className="font-medium tabular-nums">{count}</span>
              </div>
            ))}
          </div>
        )}

        {total_count === 0 && (
          <p className="text-sm text-muted-foreground text-center py-2">
            No assets recorded yet.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
