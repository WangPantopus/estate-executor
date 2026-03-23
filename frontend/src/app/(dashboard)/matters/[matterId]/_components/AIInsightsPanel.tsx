"use client";

import { useState } from "react";
import {
  Sparkles,
  Loader2,
  Plus,
  AlertTriangle,
  CheckCircle2,
  Info,
  FileText,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useSuggestTasks, useDetectAnomalies, useCreateTask } from "@/hooks";
import type {
  TaskSuggestion,
  Anomaly,
  AISuggestTasksResponse,
  AIAnomalyResponse,
  TaskPhase,
} from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Severity styling ────────────────────────────────────────────────────────

const SEVERITY_CONFIG: Record<string, { icon: typeof AlertTriangle; color: string; label: string }> = {
  high: { icon: AlertTriangle, color: "text-danger", label: "High" },
  medium: { icon: Info, color: "text-warning", label: "Medium" },
  low: { icon: Info, color: "text-muted-foreground", label: "Low" },
};

const PHASE_LABELS: Record<string, string> = {
  immediate: "Immediate",
  asset_inventory: "Asset Inventory",
  notification: "Notification",
  probate_filing: "Probate Filing",
  tax: "Tax",
  transfer_distribution: "Transfer & Distribution",
  family_communication: "Family Communication",
  closing: "Closing",
  custom: "Custom",
};

// ─── Suggestion Card ─────────────────────────────────────────────────────────

function SuggestionCard({
  suggestion,
  onAccept,
  isAccepting,
  isAccepted,
}: {
  suggestion: TaskSuggestion;
  onAccept: () => void;
  isAccepting: boolean;
  isAccepted: boolean;
}) {
  return (
    <div className="rounded-md border border-border p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{suggestion.title}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{suggestion.description}</p>
        </div>
        <Badge variant="outline" className="text-[10px] shrink-0">
          {PHASE_LABELS[suggestion.phase] ?? suggestion.phase}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground italic">
        {suggestion.reasoning}
      </p>
      <div className="flex justify-end">
        {isAccepted ? (
          <Badge variant="success" className="text-xs">
            <CheckCircle2 className="size-3 mr-0.5" />
            Added
          </Badge>
        ) : (
          <Button
            size="sm"
            variant="outline"
            onClick={onAccept}
            disabled={isAccepting}
          >
            {isAccepting ? (
              <Loader2 className="size-3.5 mr-1 animate-spin" />
            ) : (
              <Plus className="size-3.5 mr-1" />
            )}
            Add Task
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Anomaly Card ────────────────────────────────────────────────────────────

function AnomalyCard({ anomaly }: { anomaly: Anomaly }) {
  const config = SEVERITY_CONFIG[anomaly.severity] ?? SEVERITY_CONFIG.low;
  const Icon = config.icon;

  return (
    <div className="rounded-md border border-border p-3 space-y-1">
      <div className="flex items-start gap-2">
        <Icon className={cn("size-4 mt-0.5 shrink-0", config.color)} />
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Badge
              variant={anomaly.severity === "high" ? "danger" : anomaly.severity === "medium" ? "warning" : "muted"}
              className="text-[10px]"
            >
              {config.label}
            </Badge>
            <span className="text-[10px] text-muted-foreground capitalize">
              {anomaly.type.replace(/_/g, " ")}
            </span>
          </div>
          <p className="text-sm text-foreground mt-1">{anomaly.description}</p>
          {(anomaly.document_id || anomaly.asset_id) && (
            <div className="flex items-center gap-2 mt-1">
              {anomaly.document_id && (
                <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                  <FileText className="size-3" />
                  Doc: {anomaly.document_id.slice(0, 8)}...
                </span>
              )}
              {anomaly.asset_id && (
                <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                  <ArrowRight className="size-3" />
                  Asset: {anomaly.asset_id.slice(0, 8)}...
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main Panel ──────────────────────────────────────────────────────────────

interface AIInsightsPanelProps {
  firmId: string;
  matterId: string;
}

export function AIInsightsPanel({ firmId, matterId }: AIInsightsPanelProps) {
  const suggestTasks = useSuggestTasks(firmId, matterId);
  const detectAnomalies = useDetectAnomalies(firmId, matterId);
  const createTask = useCreateTask(firmId, matterId);

  const [suggestions, setSuggestions] = useState<AISuggestTasksResponse | null>(null);
  const [anomalies, setAnomalies] = useState<AIAnomalyResponse | null>(null);
  const [acceptedTasks, setAcceptedTasks] = useState<Set<number>>(new Set());
  const [acceptingIdx, setAcceptingIdx] = useState<number | null>(null);

  const handleSuggest = () => {
    suggestTasks.mutate(undefined, {
      onSuccess: (result) => {
        setSuggestions(result);
        setAcceptedTasks(new Set());
      },
    });
  };

  const handleDetect = () => {
    detectAnomalies.mutate(undefined, {
      onSuccess: (result) => setAnomalies(result),
    });
  };

  const handleAcceptSuggestion = (idx: number, suggestion: TaskSuggestion) => {
    setAcceptingIdx(idx);
    createTask.mutate(
      {
        title: suggestion.title,
        description: suggestion.description,
        phase: suggestion.phase as TaskPhase,
        priority: "normal",
      },
      {
        onSuccess: () => {
          setAcceptedTasks((prev) => new Set(prev).add(idx));
          setAcceptingIdx(null);
        },
        onError: () => setAcceptingIdx(null),
      },
    );
  };

  const isLoading = suggestTasks.isPending || detectAnomalies.isPending;
  const hasSuggestions = suggestions && suggestions.suggestions.length > 0;
  const hasAnomalies = anomalies && anomalies.anomalies.length > 0;
  const highSeverityCount = anomalies?.anomalies.filter(a => a.severity === "high").length ?? 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="size-4 text-primary" />
            AI Insights
            {(hasSuggestions || hasAnomalies) && (
              <Badge variant="info" className="text-[10px]">
                {(suggestions?.suggestions.length ?? 0) + (anomalies?.anomalies.length ?? 0)}
              </Badge>
            )}
            {highSeverityCount > 0 && (
              <Badge variant="danger" className="text-[10px]">
                {highSeverityCount} alert{highSeverityCount !== 1 ? "s" : ""}
              </Badge>
            )}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Action buttons */}
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleSuggest}
            disabled={isLoading}
            className="flex-1"
          >
            {suggestTasks.isPending ? (
              <Loader2 className="size-3.5 mr-1 animate-spin" />
            ) : (
              <Plus className="size-3.5 mr-1" />
            )}
            Suggest Tasks
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleDetect}
            disabled={isLoading}
            className="flex-1"
          >
            {detectAnomalies.isPending ? (
              <Loader2 className="size-3.5 mr-1 animate-spin" />
            ) : (
              <AlertTriangle className="size-3.5 mr-1" />
            )}
            Detect Anomalies
          </Button>
        </div>

        {/* Errors */}
        {suggestTasks.error && (
          <p className="text-xs text-danger">Failed to get suggestions. Try again.</p>
        )}
        {detectAnomalies.error && (
          <p className="text-xs text-danger">Failed to detect anomalies. Try again.</p>
        )}

        {/* Suggestions */}
        {hasSuggestions && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2">
              Suggested Tasks ({suggestions.suggestions.length})
            </h4>
            <div className="space-y-2">
              {suggestions.suggestions.map((s, idx) => (
                <SuggestionCard
                  key={idx}
                  suggestion={s}
                  onAccept={() => handleAcceptSuggestion(idx, s)}
                  isAccepting={acceptingIdx === idx}
                  isAccepted={acceptedTasks.has(idx)}
                />
              ))}
            </div>
          </div>
        )}

        {suggestions && !hasSuggestions && (
          <div className="rounded-md border border-success/30 bg-success-light/30 px-3 py-2 flex items-center gap-2">
            <CheckCircle2 className="size-4 text-success shrink-0" />
            <span className="text-xs text-success">
              No additional tasks needed — the current task list looks comprehensive.
            </span>
          </div>
        )}

        {/* Separator between sections */}
        {hasSuggestions && hasAnomalies && <Separator />}

        {/* Anomalies */}
        {hasAnomalies && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2">
              Detected Anomalies ({anomalies.anomalies.length})
            </h4>
            <div className="space-y-2">
              {anomalies.anomalies.map((a, idx) => (
                <AnomalyCard key={idx} anomaly={a} />
              ))}
            </div>
          </div>
        )}

        {anomalies && !hasAnomalies && (
          <div className="rounded-md border border-success/30 bg-success-light/30 px-3 py-2 flex items-center gap-2">
            <CheckCircle2 className="size-4 text-success shrink-0" />
            <span className="text-xs text-success">
              No anomalies detected — data looks consistent.
            </span>
          </div>
        )}

        {/* Empty state */}
        {!suggestions && !anomalies && !isLoading && (
          <p className="text-xs text-muted-foreground text-center py-2">
            Run AI analysis to get task suggestions and detect data anomalies.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
