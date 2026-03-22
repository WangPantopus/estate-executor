"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  Home,
  Landmark,
  TrendingUp,
  PiggyBank,
  Shield,
  Briefcase,
  Car,
  Globe,
  Package,
  Receipt,
  HelpCircle,
  FileText,
  Building2,
  Scale,
  ChevronDown,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  GripHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ENTITY_TYPE_LABELS, FUNDING_STATUS_LABELS, ASSET_TYPE_LABELS } from "@/lib/constants";
import type { Entity, AssetBrief, AssetType, EntityType, FundingStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Icons ────────────────────────────────────────────────────────────────────

const ASSET_ICONS: Record<AssetType, React.ReactNode> = {
  real_estate: <Home className="size-3.5" />,
  bank_account: <Landmark className="size-3.5" />,
  brokerage_account: <TrendingUp className="size-3.5" />,
  retirement_account: <PiggyBank className="size-3.5" />,
  life_insurance: <Shield className="size-3.5" />,
  business_interest: <Briefcase className="size-3.5" />,
  vehicle: <Car className="size-3.5" />,
  digital_asset: <Globe className="size-3.5" />,
  personal_property: <Package className="size-3.5" />,
  receivable: <Receipt className="size-3.5" />,
  other: <HelpCircle className="size-3.5" />,
};

const ENTITY_ICONS: Record<EntityType, React.ReactNode> = {
  revocable_trust: <FileText className="size-5" />,
  irrevocable_trust: <Scale className="size-5" />,
  llc: <Building2 className="size-5" />,
  flp: <Building2 className="size-5" />,
  corporation: <Building2 className="size-5" />,
  foundation: <Scale className="size-5" />,
  other: <FileText className="size-5" />,
};

const ENTITY_COLORS: Record<EntityType, string> = {
  revocable_trust: "border-blue-300 bg-blue-50",
  irrevocable_trust: "border-violet-300 bg-violet-50",
  llc: "border-emerald-300 bg-emerald-50",
  flp: "border-amber-300 bg-amber-50",
  corporation: "border-slate-300 bg-slate-50",
  foundation: "border-rose-300 bg-rose-50",
  other: "border-gray-300 bg-gray-50",
};

const FUNDING_VARIANT: Record<FundingStatus, "success" | "warning" | "danger" | "muted"> = {
  fully_funded: "success",
  partially_funded: "warning",
  unfunded: "danger",
  unknown: "muted",
};

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

// ─── Asset Mini Node ──────────────────────────────────────────────────────────

function AssetNode({
  asset,
  onClick,
  dashed,
}: {
  asset: AssetBrief;
  onClick: () => void;
  dashed?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-left transition-all hover:shadow-sm hover:border-primary/40 bg-card",
        dashed ? "border-dashed border-amber-400" : "border-border",
      )}
    >
      <span className="text-muted-foreground shrink-0">
        {ASSET_ICONS[asset.asset_type]}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-foreground truncate">{asset.title}</p>
        {asset.current_estimated_value !== null && (
          <p className="text-[10px] text-muted-foreground tabular-nums">
            {formatCurrency(asset.current_estimated_value)}
          </p>
        )}
      </div>
    </button>
  );
}

// ─── Entity Card Node ─────────────────────────────────────────────────────────

function EntityNode({
  entity,
  pourOverAssets,
  expanded,
  onToggleExpand,
  onEntityClick,
  onAssetClick,
}: {
  entity: Entity;
  pourOverAssets: AssetBrief[];
  expanded: boolean;
  onToggleExpand: () => void;
  onEntityClick: () => void;
  onAssetClick: (assetId: string) => void;
}) {
  const totalValue = entity.assets.reduce(
    (sum, a) => sum + (a.current_estimated_value ?? 0),
    0,
  );

  return (
    <div
      className={cn(
        "rounded-lg border-2 transition-shadow",
        ENTITY_COLORS[entity.entity_type],
        expanded && "shadow-md",
      )}
    >
      {/* Entity header */}
      <button
        type="button"
        onClick={onEntityClick}
        className="w-full text-left p-3 hover:opacity-90 transition-opacity"
      >
        <div className="flex items-start gap-2.5">
          <span className="text-muted-foreground mt-0.5">
            {ENTITY_ICONS[entity.entity_type]}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-foreground truncate">
              {entity.name}
            </p>
            <p className="text-xs text-muted-foreground">
              {ENTITY_TYPE_LABELS[entity.entity_type]}
            </p>
            {entity.trustee && (
              <p className="text-xs text-muted-foreground mt-0.5">
                Trustee: {entity.trustee}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <Badge variant={FUNDING_VARIANT[entity.funding_status]} className="text-[10px]">
            {FUNDING_STATUS_LABELS[entity.funding_status]}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {entity.assets.length} asset{entity.assets.length !== 1 ? "s" : ""}
          </span>
          {totalValue > 0 && (
            <span className="text-xs font-medium text-foreground tabular-nums ml-auto">
              {formatCurrency(totalValue)}
            </span>
          )}
        </div>
      </button>

      {/* Expand toggle + assets */}
      {entity.assets.length > 0 && (
        <div className="border-t border-inherit">
          <button
            type="button"
            onClick={onToggleExpand}
            className="flex items-center gap-1 w-full px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {expanded ? (
              <ChevronDown className="size-3" />
            ) : (
              <ChevronRight className="size-3" />
            )}
            {expanded ? "Hide assets" : "Show assets"}
          </button>

          {expanded && (
            <div className="px-3 pb-3 space-y-1.5">
              {entity.assets.map((asset) => (
                <AssetNode
                  key={asset.id}
                  asset={asset}
                  onClick={() => onAssetClick(asset.id)}
                />
              ))}
              {/* Pour-over candidates */}
              {pourOverAssets.map((asset) => (
                <AssetNode
                  key={`po-${asset.id}`}
                  asset={asset}
                  onClick={() => onAssetClick(asset.id)}
                  dashed
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Unassigned Group ─────────────────────────────────────────────────────────

function UnassignedGroup({
  assets,
  onAssetClick,
}: {
  assets: AssetBrief[];
  onAssetClick: (assetId: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);

  if (assets.length === 0) return null;

  const totalValue = assets.reduce(
    (sum, a) => sum + (a.current_estimated_value ?? 0),
    0,
  );

  return (
    <div className="rounded-lg border-2 border-dashed border-muted-foreground/30 bg-surface-elevated/30">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left p-3"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-muted-foreground">
              Unassigned Assets
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {assets.length} asset{assets.length !== 1 ? "s" : ""}
              {totalValue > 0 && ` · ${formatCurrency(totalValue)}`}
            </p>
          </div>
          {expanded ? (
            <ChevronDown className="size-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-1.5 border-t border-border">
          <div className="pt-2" />
          {assets.map((asset) => (
            <AssetNode
              key={asset.id}
              asset={asset}
              onClick={() => onAssetClick(asset.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Pour-Over Arrow ──────────────────────────────────────────────────────────

function PourOverIndicator({ count }: { count: number }) {
  if (count === 0) return null;

  return (
    <div className="flex items-center gap-2 px-4 py-2 rounded-md bg-amber-50 border border-dashed border-amber-300 text-xs text-amber-700">
      <svg width="24" height="12" viewBox="0 0 24 12" className="shrink-0">
        <line
          x1="0"
          y1="6"
          x2="18"
          y2="6"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeDasharray="3 3"
        />
        <polygon points="18,2 24,6 18,10" fill="currentColor" />
      </svg>
      <span>
        {count} pour-over candidate{count !== 1 ? "s" : ""} — assets flowing from probate to trust
      </span>
    </div>
  );
}

// ─── Entity Map View ──────────────────────────────────────────────────────────

interface EntityMapViewProps {
  entities: Entity[];
  unassignedAssets: AssetBrief[];
  pourOverCandidates: AssetBrief[];
  onEntityClick: (entityId: string) => void;
  onAssetClick: (assetId: string) => void;
}

export function EntityMapView({
  entities,
  unassignedAssets,
  pourOverCandidates,
  onEntityClick,
  onAssetClick,
}: EntityMapViewProps) {
  const [expandedEntities, setExpandedEntities] = useState<Set<string>>(
    () => new Set(entities.length <= 3 ? entities.map((e) => e.id) : []),
  );
  const [scale, setScale] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  const toggleExpand = useCallback((entityId: string) => {
    setExpandedEntities((prev) => {
      const next = new Set(prev);
      if (next.has(entityId)) next.delete(entityId);
      else next.add(entityId);
      return next;
    });
  }, []);

  const zoomIn = () => setScale((s) => Math.min(s + 0.15, 1.5));
  const zoomOut = () => setScale((s) => Math.max(s - 0.15, 0.5));
  const resetZoom = () => setScale(1);

  // Build map of pour-over candidates by target entity (first entity with trust type)
  const pourOverByEntity = new Map<string, AssetBrief[]>();
  if (pourOverCandidates.length > 0) {
    const trustEntity = entities.find(
      (e) =>
        e.entity_type === "revocable_trust" ||
        e.entity_type === "irrevocable_trust",
    );
    if (trustEntity) {
      pourOverByEntity.set(trustEntity.id, pourOverCandidates);
    }
  }

  const isEmpty = entities.length === 0 && unassignedAssets.length === 0;

  if (isEmpty) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center">
        <Building2 className="size-10 text-muted-foreground/30 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">
          No entities or assets to visualize.
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Create an entity to start building the ownership map.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-elevated/30">
        <p className="text-xs font-medium text-muted-foreground">
          Ownership Map
        </p>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={zoomOut} className="size-7">
            <ZoomOut className="size-3.5" />
          </Button>
          <span className="text-xs text-muted-foreground tabular-nums w-10 text-center">
            {Math.round(scale * 100)}%
          </span>
          <Button variant="ghost" size="icon" onClick={zoomIn} className="size-7">
            <ZoomIn className="size-3.5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={resetZoom} className="size-7">
            <Maximize2 className="size-3.5" />
          </Button>
        </div>
      </div>

      {/* Pour-over indicator */}
      {pourOverCandidates.length > 0 && (
        <div className="px-4 pt-3">
          <PourOverIndicator count={pourOverCandidates.length} />
        </div>
      )}

      {/* Map content */}
      <ScrollArea className="max-h-[600px]">
        <div
          ref={containerRef}
          className="p-6 transition-transform origin-top-left"
          style={{ transform: `scale(${scale})`, transformOrigin: "top left" }}
        >
          {/* Entity grid */}
          <div
            className={cn(
              "grid gap-5",
              entities.length === 1
                ? "grid-cols-1 max-w-md mx-auto"
                : entities.length === 2
                  ? "grid-cols-1 sm:grid-cols-2 max-w-2xl mx-auto"
                  : entities.length <= 4
                    ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-2"
                    : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
            )}
          >
            {entities.map((entity) => (
              <EntityNode
                key={entity.id}
                entity={entity}
                pourOverAssets={pourOverByEntity.get(entity.id) ?? []}
                expanded={expandedEntities.has(entity.id)}
                onToggleExpand={() => toggleExpand(entity.id)}
                onEntityClick={() => onEntityClick(entity.id)}
                onAssetClick={onAssetClick}
              />
            ))}
          </div>

          {/* Unassigned assets */}
          {unassignedAssets.length > 0 && (
            <div className="mt-5">
              <UnassignedGroup
                assets={unassignedAssets}
                onAssetClick={onAssetClick}
              />
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Legend */}
      <div className="flex items-center gap-4 px-4 py-2 border-t border-border text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5 bg-border rounded" />
          Owned asset
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5 border-t border-dashed border-amber-400" />
          Pour-over candidate
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5 border-t-2 border-dashed border-muted-foreground/30 rounded" />
          Unassigned
        </span>
      </div>
    </div>
  );
}
