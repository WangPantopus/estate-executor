"use client";

import { useState } from "react";
import {
  X,
  UserCircle,
  Shield,
  FileText,
  Link2,
  Trash2,
  Loader2,
  Pencil,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ENTITY_TYPE_LABELS,
  FUNDING_STATUS_LABELS,
  ASSET_TYPE_LABELS,
} from "@/lib/constants";
import { useUpdateEntity, useDeleteEntity } from "@/hooks";
import type { Entity, AssetBrief, FundingStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const FUNDING_VARIANT: Record<FundingStatus, "success" | "warning" | "danger" | "muted"> = {
  fully_funded: "success",
  partially_funded: "warning",
  unfunded: "danger",
  unknown: "muted",
};

const FUNDING_DESCRIPTIONS: Record<FundingStatus, string> = {
  fully_funded: "All intended assets have been transferred to the entity.",
  partially_funded: "Some but not all intended assets have been transferred.",
  unfunded: "No assets have been transferred to this entity yet.",
  unknown: "Funding status has not been determined.",
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatJsonField(obj: Record<string, unknown> | null): string {
  if (!obj || Object.keys(obj).length === 0) return "Not specified";
  return Object.entries(obj)
    .map(([key, value]) => `${key.replace(/_/g, " ")}: ${String(value)}`)
    .join("\n");
}

// ─── Panel ────────────────────────────────────────────────────────────────────

interface EntityDetailPanelProps {
  entity: Entity;
  firmId: string;
  matterId: string;
  onClose: () => void;
  onAssetClick: (assetId: string) => void;
}

export function EntityDetailPanel({
  entity,
  firmId,
  matterId,
  onClose,
  onAssetClick,
}: EntityDetailPanelProps) {
  const updateEntity = useUpdateEntity(firmId, matterId);
  const deleteEntity = useDeleteEntity(firmId, matterId);

  const totalValue = entity.assets.reduce(
    (sum, a) => sum + (a.current_estimated_value ?? 0),
    0,
  );

  const handleDelete = () => {
    if (confirm(`Delete "${entity.name}"? This will unlink all assets but not delete them.`)) {
      deleteEntity.mutate(entity.id, {
        onSuccess: () => onClose(),
      });
    }
  };

  const handleFundingChange = (status: FundingStatus) => {
    updateEntity.mutate({
      entityId: entity.id,
      data: { funding_status: status },
    });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border gap-2">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">
            {ENTITY_TYPE_LABELS[entity.entity_type]}
          </p>
          <h2 className="text-lg font-medium text-foreground">{entity.name}</h2>
          <div className="flex items-center gap-2 mt-1">
            <Badge
              variant={FUNDING_VARIANT[entity.funding_status]}
              className="text-[10px]"
            >
              {FUNDING_STATUS_LABELS[entity.funding_status]}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {entity.assets.length} asset{entity.assets.length !== 1 ? "s" : ""}
              {totalValue > 0 && ` · ${formatCurrency(totalValue)}`}
            </span>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
          <X className="size-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-5">
          {/* Trustee info */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <UserCircle className="size-3.5 inline mr-1" />
              Trustee Information
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-muted-foreground">Trustee</p>
                <p className="text-sm text-foreground">{entity.trustee ?? "Not specified"}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Successor Trustee</p>
                <p className="text-sm text-foreground">
                  {entity.successor_trustee ?? "Not specified"}
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Funding status */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <Shield className="size-3.5 inline mr-1" />
              Funding Status
            </h3>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={FUNDING_VARIANT[entity.funding_status]}>
                {FUNDING_STATUS_LABELS[entity.funding_status]}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              {FUNDING_DESCRIPTIONS[entity.funding_status]}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(
                ["unknown", "unfunded", "partially_funded", "fully_funded"] as FundingStatus[]
              ).map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => handleFundingChange(status)}
                  disabled={entity.funding_status === status || updateEntity.isPending}
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
                    entity.funding_status === status
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground disabled:opacity-50",
                  )}
                >
                  {FUNDING_STATUS_LABELS[status]}
                </button>
              ))}
            </div>
          </div>

          <Separator />

          {/* Trigger conditions */}
          {entity.trigger_conditions &&
            Object.keys(entity.trigger_conditions).length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">
                  Trigger Conditions
                </h3>
                <pre className="text-xs text-foreground bg-surface-elevated rounded-md p-3 whitespace-pre-wrap font-mono">
                  {formatJsonField(entity.trigger_conditions)}
                </pre>
              </div>
            )}

          {/* Distribution rules */}
          {entity.distribution_rules &&
            Object.keys(entity.distribution_rules).length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">
                  <FileText className="size-3.5 inline mr-1" />
                  Distribution Rules
                </h3>
                <pre className="text-xs text-foreground bg-surface-elevated rounded-md p-3 whitespace-pre-wrap font-mono">
                  {formatJsonField(entity.distribution_rules)}
                </pre>
              </div>
            )}

          <Separator />

          {/* Linked assets */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <Link2 className="size-3.5 inline mr-1" />
              Linked Assets ({entity.assets.length})
            </h3>
            {entity.assets.length > 0 ? (
              <div className="space-y-1.5">
                {entity.assets.map((asset) => (
                  <button
                    key={asset.id}
                    type="button"
                    onClick={() => onAssetClick(asset.id)}
                    className="flex items-center justify-between w-full rounded-md bg-surface-elevated px-3 py-2 text-sm hover:bg-surface-elevated/80 transition-colors text-left"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-foreground truncate">
                        {asset.title}
                      </p>
                      <p className="text-xs text-muted-foreground capitalize">
                        {ASSET_TYPE_LABELS[asset.asset_type]}
                      </p>
                    </div>
                    {asset.current_estimated_value !== null && (
                      <span className="text-sm font-medium tabular-nums text-foreground shrink-0 ml-2">
                        {formatCurrency(asset.current_estimated_value)}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No assets linked.</p>
            )}
          </div>

          {/* Metadata */}
          <div className="text-xs text-muted-foreground">
            <p>
              Created:{" "}
              {new Date(entity.created_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </p>
            <p>
              Updated:{" "}
              {new Date(entity.updated_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </p>
          </div>
        </div>
      </ScrollArea>

      {/* Actions */}
      <div className="border-t border-border p-4 flex items-center gap-2">
        <Button
          variant="destructive"
          size="sm"
          onClick={handleDelete}
          disabled={deleteEntity.isPending}
        >
          {deleteEntity.isPending ? (
            <Loader2 className="size-4 mr-1 animate-spin" />
          ) : (
            <Trash2 className="size-4 mr-1" />
          )}
          Delete Entity
        </Button>
      </div>
    </div>
  );
}
