"use client";

import {
  Sparkles,
  Loader2,
  Activity,
  DollarSign,
  Zap,
  AlertTriangle,
  CheckCircle2,
  BarChart3,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useAIUsageStats } from "@/hooks";
import type { AIUsageByOperation, AIUsageByMatter } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatCost(usd: number): string {
  if (usd < 0.01 && usd > 0) return "<$0.01";
  return `$${usd.toFixed(2)}`;
}

const OPERATION_LABELS: Record<string, string> = {
  classify: "Classification",
  extract: "Data Extraction",
  draft_letter: "Letter Drafting",
  suggest_tasks: "Task Suggestions",
  detect_anomalies: "Anomaly Detection",
  trust_analysis: "Trust Analysis",
};

const OPERATION_COLORS: Record<string, string> = {
  classify: "bg-blue-500",
  extract: "bg-violet-500",
  draft_letter: "bg-emerald-500",
  suggest_tasks: "bg-amber-500",
  detect_anomalies: "bg-rose-500",
  trust_analysis: "bg-cyan-500",
};

// ─── Metric Card ─────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
}: {
  label: string;
  value: string;
  subtitle?: string;
  icon: typeof Activity;
  variant?: "default" | "success" | "warning" | "danger";
}) {
  const colors = {
    default: "text-primary",
    success: "text-success",
    warning: "text-warning",
    danger: "text-danger",
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={cn("shrink-0", colors[variant])}>
            <Icon className="size-5" />
          </div>
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-xl font-bold text-foreground tabular-nums">{value}</p>
            {subtitle && (
              <p className="text-[10px] text-muted-foreground">{subtitle}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Rate Limit Gauge ────────────────────────────────────────────────────────

function RateLimitGauge({
  current,
  limit,
  label,
}: {
  current: number;
  limit: number;
  label: string;
}) {
  const pct = limit > 0 ? Math.min((current / limit) * 100, 100) : 0;
  const isHigh = pct >= 80;
  const isCritical = pct >= 95;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn(
          "tabular-nums font-medium",
          isCritical ? "text-danger" : isHigh ? "text-warning" : "text-foreground",
        )}>
          {current} / {limit}
        </span>
      </div>
      <Progress
        value={pct}
        className={cn(
          "h-2",
          isCritical ? "[&>div]:bg-danger" : isHigh ? "[&>div]:bg-warning" : "",
        )}
      />
    </div>
  );
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

interface AIUsageDashboardProps {
  firmId: string;
  matterId: string;
}

export function AIUsageDashboard({ firmId, matterId }: AIUsageDashboardProps) {
  const { data: stats, isLoading, error } = useAIUsageStats(firmId, matterId);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-12 flex items-center justify-center">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error || !stats) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-sm text-danger">Failed to load AI usage stats.</p>
        </CardContent>
      </Card>
    );
  }

  const periodLabel = new Date(stats.period_start).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Sparkles className="size-5 text-primary" />
        <div>
          <h2 className="text-lg font-semibold text-foreground">AI Usage Monitor</h2>
          <p className="text-xs text-muted-foreground">Usage for {periodLabel}</p>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="API Calls"
          value={String(stats.total_calls)}
          subtitle={`${stats.successful_calls} successful, ${stats.failed_calls} failed`}
          icon={Activity}
        />
        <MetricCard
          label="Tokens Used"
          value={formatTokens(stats.total_input_tokens + stats.total_output_tokens)}
          subtitle={`${formatTokens(stats.total_input_tokens)} in, ${formatTokens(stats.total_output_tokens)} out`}
          icon={Zap}
        />
        <MetricCard
          label="Estimated Cost"
          value={formatCost(stats.total_cost_usd)}
          subtitle="This billing period"
          icon={DollarSign}
          variant={stats.total_cost_usd > 50 ? "warning" : "default"}
        />
        <MetricCard
          label="Success Rate"
          value={
            stats.total_calls > 0
              ? `${Math.round((stats.successful_calls / stats.total_calls) * 100)}%`
              : "—"
          }
          subtitle={stats.failed_calls > 0 ? `${stats.failed_calls} errors` : "No errors"}
          icon={stats.failed_calls > 0 ? AlertTriangle : CheckCircle2}
          variant={stats.failed_calls > 0 ? "warning" : "success"}
        />
      </div>

      {/* Rate limits */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Rate Limit Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <RateLimitGauge
            current={stats.rate_limits.firm_calls_this_hour}
            limit={stats.rate_limits.firm_limit_per_hour}
            label="Firm (per hour)"
          />
        </CardContent>
      </Card>

      {/* Two-column: by operation + by matter */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* By operation */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-1.5">
              <BarChart3 className="size-4" />
              Usage by Operation
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.by_operation.length > 0 ? (
              <div className="space-y-2.5">
                {stats.by_operation.map((op: AIUsageByOperation) => (
                  <div key={op.operation} className="flex items-center gap-3">
                    <div className={cn(
                      "size-2.5 rounded-full shrink-0",
                      OPERATION_COLORS[op.operation] ?? "bg-gray-400",
                    )} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-foreground">
                          {OPERATION_LABELS[op.operation] ?? op.operation}
                        </span>
                        <span className="text-xs text-muted-foreground tabular-nums">
                          {op.calls} call{op.calls !== 1 ? "s" : ""}
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-0.5">
                        <span className="text-[10px] text-muted-foreground">
                          {formatTokens(op.input_tokens + op.output_tokens)} tokens
                        </span>
                        <span className="text-[10px] font-medium text-foreground tabular-nums">
                          {formatCost(op.cost_usd)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No AI operations this period.
              </p>
            )}
          </CardContent>
        </Card>

        {/* By matter */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-1.5">
              <BarChart3 className="size-4" />
              Usage by Matter
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.by_matter.length > 0 ? (
              <div className="space-y-2">
                {stats.by_matter.map((m: AIUsageByMatter) => (
                  <div
                    key={m.matter_id}
                    className="flex items-center justify-between rounded-md bg-surface-elevated px-3 py-2"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-foreground truncate">{m.matter_title}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {m.calls} call{m.calls !== 1 ? "s" : ""}
                      </p>
                    </div>
                    <Badge variant="outline" className="text-xs tabular-nums shrink-0 ml-2">
                      {formatCost(m.cost_usd)}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No matter-level usage this period.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
