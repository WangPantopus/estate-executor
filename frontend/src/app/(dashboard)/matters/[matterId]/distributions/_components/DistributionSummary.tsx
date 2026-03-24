"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { DollarSign, Users, CheckCircle2, Clock } from "lucide-react";
import type { DistributionSummaryResponse } from "@/lib/types";

const TYPE_LABELS: Record<string, string> = {
  cash: "Cash",
  asset_transfer: "Asset Transfer",
  in_kind: "In Kind",
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

interface DistributionSummaryProps {
  summary: DistributionSummaryResponse;
  estimatedTotal?: number | null;
}

export function DistributionSummary({ summary, estimatedTotal }: DistributionSummaryProps) {
  const ackPct =
    summary.total_distributions > 0
      ? (summary.total_acknowledged / summary.total_distributions) * 100
      : 0;

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex size-9 items-center justify-center rounded-lg bg-emerald-50">
                <DollarSign className="size-4 text-emerald-600" />
              </div>
              <span className="text-xs font-medium text-muted-foreground">Total Distributed</span>
            </div>
            <p className="text-xl font-semibold">{formatCurrency(summary.total_distributed)}</p>
            {estimatedTotal != null && estimatedTotal > 0 && (
              <p className="text-xs text-muted-foreground mt-1">
                of {formatCurrency(estimatedTotal)} estimated
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex size-9 items-center justify-center rounded-lg bg-blue-50">
                <Users className="size-4 text-blue-600" />
              </div>
              <span className="text-xs font-medium text-muted-foreground">Distributions</span>
            </div>
            <p className="text-xl font-semibold">{summary.total_distributions}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {summary.by_beneficiary.length} beneficiar{summary.by_beneficiary.length !== 1 ? "ies" : "y"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex size-9 items-center justify-center rounded-lg bg-emerald-50">
                <CheckCircle2 className="size-4 text-emerald-600" />
              </div>
              <span className="text-xs font-medium text-muted-foreground">Acknowledged</span>
            </div>
            <p className="text-xl font-semibold">{summary.total_acknowledged}</p>
            <Progress value={ackPct} className="h-1.5 mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex size-9 items-center justify-center rounded-lg bg-amber-50">
                <Clock className="size-4 text-amber-600" />
              </div>
              <span className="text-xs font-medium text-muted-foreground">Pending</span>
            </div>
            <p className="text-xl font-semibold">{summary.total_pending}</p>
            <p className="text-xs text-muted-foreground mt-1">awaiting acknowledgment</p>
          </CardContent>
        </Card>
      </div>

      {/* By beneficiary */}
      {summary.by_beneficiary.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <h3 className="text-sm font-medium text-foreground mb-4">By Beneficiary</h3>
            <div className="space-y-3">
              {summary.by_beneficiary.map((b) => (
                <div key={b.stakeholder_id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary">
                      {b.beneficiary_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{b.beneficiary_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {b.distribution_count} distribution{b.distribution_count !== 1 ? "s" : ""}
                        {b.pending_count > 0 && (
                          <span className="text-amber-600"> ({b.pending_count} pending)</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm font-semibold">{formatCurrency(b.total_distributed)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* By type */}
      {Object.keys(summary.by_type).length > 0 && (
        <Card>
          <CardContent className="p-5">
            <h3 className="text-sm font-medium text-foreground mb-3">By Type</h3>
            <div className="flex flex-wrap gap-3">
              {Object.entries(summary.by_type).map(([type, total]) => (
                <Badge key={type} variant="outline" className="px-3 py-1.5 text-sm gap-2">
                  <span className="text-muted-foreground">
                    {TYPE_LABELS[type] ?? type}
                  </span>
                  <span className="font-semibold">{formatCurrency(total)}</span>
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
