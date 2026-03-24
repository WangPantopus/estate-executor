"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import {
  useDistributions,
  useDistributionSummary,
  useRecordDistribution,
  useStakeholders,
  useAssets,
  useMatterDashboard,
} from "@/hooks/use-queries";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import { EmptyState } from "@/components/layout/EmptyState";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Clock, FileText, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { RecordDistributionDialog } from "./_components/RecordDistributionDialog";
import { DistributionSummary } from "./_components/DistributionSummary";
import type { DistributionType, StakeholderRole } from "@/lib/types";

const FIRM_ID = "current";

const TYPE_LABELS: Record<string, string> = {
  cash: "Cash",
  asset_transfer: "Asset Transfer",
  in_kind: "In Kind",
};

const TYPE_COLORS: Record<string, string> = {
  cash: "bg-emerald-50 text-emerald-700 border-emerald-200",
  asset_transfer: "bg-blue-50 text-blue-700 border-blue-200",
  in_kind: "bg-purple-50 text-purple-700 border-purple-200",
};

function formatCurrency(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function DistributionsPage() {
  const params = useParams();
  const matterId = params.matterId as string;
  const [tab, setTab] = useState("ledger");

  const { data: distData, isLoading: distLoading } = useDistributions(FIRM_ID, matterId);
  const { data: summaryData, isLoading: summaryLoading } = useDistributionSummary(FIRM_ID, matterId);
  const { data: stakeholderData } = useStakeholders(FIRM_ID, matterId);
  const { data: assetData } = useAssets(FIRM_ID, matterId);
  const { data: dashData } = useMatterDashboard(FIRM_ID, matterId);
  const recordDist = useRecordDistribution(FIRM_ID, matterId);

  const beneficiaries = (stakeholderData?.data ?? []).filter(
    (s) => s.role === ("beneficiary" as StakeholderRole),
  );
  const assets = assetData?.data ?? [];
  const distributions = distData?.data ?? [];

  const handleRecord = async (data: {
    beneficiary_stakeholder_id: string;
    asset_id?: string | null;
    amount?: number | null;
    description: string;
    distribution_type: DistributionType;
    distribution_date: string;
    notes?: string | null;
  }) => {
    await recordDist.mutateAsync(data);
  };

  const handleExportPDF = () => {
    // Trigger browser print with print-optimized CSS
    window.print();
  };

  if (distLoading) {
    return <LoadingState variant="table" />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <PageHeader
          title="Distribution Ledger"
          subtitle="Track distributions to beneficiaries"
        />
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={handleExportPDF}>
            <Download className="size-3.5" />
            <span className="hidden sm:inline">Export PDF</span>
          </Button>
          <RecordDistributionDialog
            beneficiaries={beneficiaries}
            assets={assets}
            onSubmit={handleRecord}
            isPending={recordDist.isPending}
          />
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="ledger">Ledger</TabsTrigger>
          <TabsTrigger value="summary">Summary</TabsTrigger>
        </TabsList>

        {/* Ledger Tab */}
        <TabsContent value="ledger" className="mt-6">
          {distributions.length === 0 ? (
            <EmptyState
              icon={<FileText className="size-12" />}
              title="No distributions recorded"
              description="Record distributions as assets are transferred or cash is disbursed to beneficiaries."
            />
          ) : (
            <div className="rounded-lg border border-border overflow-hidden print:border-0">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead>Beneficiary</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Asset Source</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {distributions.map((dist) => (
                    <TableRow key={dist.id}>
                      <TableCell className="font-medium">
                        {dist.beneficiary_name}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">{dist.description}</span>
                        {dist.notes && (
                          <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-48">
                            {dist.notes}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {formatCurrency(dist.amount)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn("text-xs", TYPE_COLORS[dist.distribution_type] ?? "")}
                        >
                          {TYPE_LABELS[dist.distribution_type] ?? dist.distribution_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                        {formatDate(dist.distribution_date)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {dist.asset_title ?? "—"}
                      </TableCell>
                      <TableCell>
                        {dist.receipt_acknowledged ? (
                          <div className="flex items-center gap-1.5 text-emerald-600">
                            <CheckCircle2 className="size-3.5" />
                            <span className="text-xs font-medium">Acknowledged</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 text-amber-600">
                            <Clock className="size-3.5" />
                            <span className="text-xs font-medium">Pending</span>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Print footer */}
          <div className="hidden print:block mt-8 pt-4 border-t text-xs text-muted-foreground">
            <p>Distribution Ledger — {dashData?.matter.decedent_name ?? "Estate"}</p>
            <p>Generated {new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}</p>
            <p>Estate Executor OS — Confidential</p>
          </div>
        </TabsContent>

        {/* Summary Tab */}
        <TabsContent value="summary" className="mt-6">
          {summaryLoading ? (
            <LoadingState variant="cards" />
          ) : summaryData ? (
            <DistributionSummary
              summary={summaryData}
              estimatedTotal={dashData?.matter.estimated_value}
            />
          ) : (
            <EmptyState
              icon={<FileText className="size-12" />}
              title="No distribution data"
              description="Record distributions to see the summary."
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
