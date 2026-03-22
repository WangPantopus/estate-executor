"use client";

import { useState } from "react";
import {
  X,
  Paperclip,
  Upload,
  Link2,
  CheckCircle2,
  Sparkles,
  Pencil,
  Trash2,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { StatusBadge } from "@/components/layout/StatusBadge";
import {
  ASSET_TYPE_LABELS,
  OWNERSHIP_TYPE_LABELS,
  TRANSFER_MECHANISM_LABELS,
  ASSET_STATUS_ORDER,
  ASSET_STATUS_LABELS,
} from "@/lib/constants";
import { useAsset, useUpdateAsset, useAddValuation } from "@/hooks";
import type { AssetListItem, AssetDetail, AssetStatus, Entity } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ASSET_TYPE_ICONS, ASSET_TYPE_COLORS } from "./AssetCard";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// Valid next statuses for lifecycle transitions
const VALID_TRANSITIONS: Record<AssetStatus, AssetStatus[]> = {
  discovered: ["valued"],
  valued: ["transferred"],
  transferred: ["distributed"],
  distributed: [],
};

// ─── Valuation Card ───────────────────────────────────────────────────────────

function ValuationCard({
  label,
  value,
  type,
  assetId,
  firmId,
  matterId,
}: {
  label: string;
  value: number | null;
  type: string;
  assetId: string;
  firmId: string;
  matterId: string;
}) {
  const addValuation = useAddValuation(firmId, matterId);
  const [editing, setEditing] = useState(false);
  const [inputVal, setInputVal] = useState("");

  const handleSave = () => {
    const num = parseFloat(inputVal.replace(/[,$]/g, ""));
    if (!isNaN(num) && num >= 0) {
      addValuation.mutate(
        { assetId, data: { type, value: num } },
        { onSuccess: () => setEditing(false) },
      );
    }
  };

  return (
    <div className="rounded-md border border-border p-3">
      <p className="text-xs font-medium text-muted-foreground mb-1">{label}</p>
      {editing ? (
        <div className="flex items-center gap-2">
          <Input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="0"
            className="h-8 text-sm"
            autoFocus
          />
          <Button
            size="sm"
            onClick={handleSave}
            disabled={addValuation.isPending}
            className="h-8"
          >
            {addValuation.isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              "Save"
            )}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setEditing(false)}
            className="h-8"
          >
            Cancel
          </Button>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <p className="text-lg font-semibold text-foreground tabular-nums">
            {value !== null ? formatCurrency(value) : "—"}
          </p>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setInputVal(value?.toString() ?? "");
              setEditing(true);
            }}
            className="h-7 text-xs"
          >
            <Pencil className="size-3 mr-1" />
            Update
          </Button>
        </div>
      )}
    </div>
  );
}

// ─── AI Extracted Data ────────────────────────────────────────────────────────

function AIExtractedDataCard({
  data,
}: {
  data: Record<string, unknown>;
}) {
  const entries = Object.entries(data).filter(
    ([, v]) => v !== null && v !== undefined && v !== "",
  );
  if (entries.length === 0) return null;

  return (
    <div className="rounded-md border border-info/30 bg-info-light/30 p-3">
      <div className="flex items-center gap-1.5 mb-2">
        <Sparkles className="size-4 text-info" />
        <span className="text-xs font-medium text-info">AI Suggested Data</span>
      </div>
      <div className="space-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center justify-between text-sm">
            <div className="min-w-0">
              <span className="text-muted-foreground text-xs capitalize">
                {key.replace(/_/g, " ")}:
              </span>{" "}
              <span className="text-foreground">{String(value)}</span>
            </div>
            <Badge variant="info" className="text-[10px] shrink-0 ml-2">
              AI Suggested
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Panel ────────────────────────────────────────────────────────────────────

interface AssetDetailPanelProps {
  assetId: string;
  firmId: string;
  matterId: string;
  assets: AssetListItem[];
  entities: Entity[];
  onClose: () => void;
}

export function AssetDetailPanel({
  assetId,
  firmId,
  matterId,
  assets,
  entities,
  onClose,
}: AssetDetailPanelProps) {
  const { data: assetDetail, isLoading } = useAsset(firmId, matterId, assetId);
  const updateAsset = useUpdateAsset(firmId, matterId);

  // Fallback to list item while detail loads
  const asset: AssetListItem | AssetDetail | undefined =
    assetDetail ?? assets.find((a) => a.id === assetId);

  if (isLoading && !asset) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="h-5 w-40 bg-surface-elevated rounded animate-pulse" />
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>
        <div className="p-4 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-surface-elevated rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Asset not found.</p>
      </div>
    );
  }

  const detail = assetDetail as AssetDetail | undefined;
  const nextStatuses = VALID_TRANSITIONS[asset.status];
  const linkedEntity = asset.entities.length > 0 ? asset.entities[0] : null;

  const handleStatusTransition = (newStatus: AssetStatus) => {
    updateAsset.mutate({ assetId: asset.id, data: { status: newStatus } });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={cn(
              "flex items-center justify-center size-10 rounded-lg shrink-0",
              ASSET_TYPE_COLORS[asset.asset_type],
            )}
          >
            {ASSET_TYPE_ICONS[asset.asset_type]}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <StatusBadge status={asset.status} />
            </div>
            <h2 className="text-lg font-medium text-foreground truncate">
              {asset.title}
            </h2>
            <p className="text-xs text-muted-foreground">
              {ASSET_TYPE_LABELS[asset.asset_type]}
              {asset.institution && ` · ${asset.institution}`}
            </p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
          <X className="size-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-5">
          {/* Account number (masked) */}
          {asset.account_number_masked && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Account Number</p>
              <p className="text-sm font-mono text-foreground">{asset.account_number_masked}</p>
            </div>
          )}

          {/* Description */}
          {asset.description && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Description</p>
              <p className="text-sm text-foreground whitespace-pre-wrap">{asset.description}</p>
            </div>
          )}

          <Separator />

          {/* Valuations */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-3">Valuations</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <ValuationCard
                label="Date of Death Value"
                value={asset.date_of_death_value}
                type="date_of_death"
                assetId={asset.id}
                firmId={firmId}
                matterId={matterId}
              />
              <ValuationCard
                label="Current Estimate"
                value={asset.current_estimated_value}
                type="current_estimate"
                assetId={asset.id}
                firmId={firmId}
                matterId={matterId}
              />
              <ValuationCard
                label="Final Appraised"
                value={asset.final_appraised_value}
                type="final_appraised"
                assetId={asset.id}
                firmId={firmId}
                matterId={matterId}
              />
            </div>

            {/* Valuation history */}
            {detail?.valuations && detail.valuations.length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-muted-foreground mb-1">History</p>
                <div className="space-y-1">
                  {detail.valuations.map((v, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground capitalize">
                        {v.type.replace(/_/g, " ")}
                      </span>
                      <span className="font-medium tabular-nums">
                        {formatCurrency(v.value)}
                      </span>
                      <span className="text-muted-foreground">
                        {formatDate(v.recorded_at)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Ownership & Transfer */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">Ownership & Transfer</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-muted-foreground mb-0.5">Ownership Type</p>
                <p className="text-sm text-foreground">
                  {asset.ownership_type
                    ? OWNERSHIP_TYPE_LABELS[asset.ownership_type]
                    : "Not specified"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-0.5">Transfer Mechanism</p>
                <p className="text-sm text-foreground">
                  {asset.transfer_mechanism
                    ? TRANSFER_MECHANISM_LABELS[asset.transfer_mechanism]
                    : "Not specified"}
                </p>
              </div>
            </div>

            {/* Linked entity */}
            {linkedEntity && (
              <div className="mt-3 rounded-md bg-surface-elevated p-3 flex items-center gap-2">
                <Link2 className="size-4 text-muted-foreground shrink-0" />
                <div>
                  <p className="text-sm font-medium text-foreground">{linkedEntity.name}</p>
                  <p className="text-xs text-muted-foreground capitalize">
                    {linkedEntity.entity_type.replace(/_/g, " ")}
                  </p>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Documents */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <Paperclip className="size-3.5 inline mr-1" />
              Documents ({detail?.documents?.length ?? asset.document_count})
            </h3>
            {detail?.documents && detail.documents.length > 0 ? (
              <div className="space-y-1">
                {detail.documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-2 text-sm rounded-md bg-surface-elevated px-3 py-2"
                  >
                    <Paperclip className="size-3.5 text-muted-foreground" />
                    <span className="truncate text-foreground">{doc.filename}</span>
                    {doc.doc_type && (
                      <Badge variant="muted" className="text-[10px] ml-auto">
                        {doc.doc_type}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No documents linked.</p>
            )}
            <div className="flex gap-2 mt-2">
              <Button variant="outline" size="sm" disabled>
                <Upload className="size-3.5 mr-1" />
                Upload
              </Button>
              <Button variant="outline" size="sm" disabled>
                <Link2 className="size-3.5 mr-1" />
                Link existing
              </Button>
            </div>
          </div>

          {/* AI Extracted Data */}
          {asset.metadata && Object.keys(asset.metadata).length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">AI Extracted Data</h3>
                <AIExtractedDataCard data={asset.metadata} />
              </div>
            </>
          )}

          {/* Status lifecycle */}
          <Separator />
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">Status Lifecycle</h3>
            <div className="flex items-center gap-2">
              {ASSET_STATUS_ORDER.map((status, idx) => {
                const currentIdx = ASSET_STATUS_ORDER.indexOf(asset.status);
                const isActive = idx <= currentIdx;
                const isCurrent = status === asset.status;
                return (
                  <div key={status} className="flex items-center gap-2">
                    {idx > 0 && (
                      <div
                        className={cn(
                          "h-px w-4",
                          isActive ? "bg-success" : "bg-border",
                        )}
                      />
                    )}
                    <div
                      className={cn(
                        "flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium border transition-colors",
                        isCurrent
                          ? "border-primary bg-primary/10 text-primary"
                          : isActive
                            ? "border-success/30 bg-success-light text-success"
                            : "border-border text-muted-foreground",
                      )}
                    >
                      {isActive && idx < currentIdx && (
                        <CheckCircle2 className="size-3" />
                      )}
                      {ASSET_STATUS_LABELS[status]}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </ScrollArea>

      {/* Action footer */}
      <div className="border-t border-border p-4 flex items-center gap-2">
        {nextStatuses.map((nextStatus) => (
          <Button
            key={nextStatus}
            size="sm"
            onClick={() => handleStatusTransition(nextStatus)}
            disabled={updateAsset.isPending}
            className="flex-1"
          >
            {updateAsset.isPending && <Loader2 className="size-4 mr-1 animate-spin" />}
            Mark as {ASSET_STATUS_LABELS[nextStatus]}
          </Button>
        ))}
        {nextStatuses.length === 0 && (
          <p className="text-sm text-muted-foreground">
            This asset has been fully distributed.
          </p>
        )}
      </div>
    </div>
  );
}
