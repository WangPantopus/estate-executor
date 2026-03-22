"use client";

import { use, useState, useMemo } from "react";
import { Plus, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
} from "@/components/ui/sheet";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import { EmptyState } from "@/components/layout/EmptyState";
import { useAssets, useEntities } from "@/hooks";
import type { AssetListItem } from "@/lib/types";

import {
  AssetSummaryBar,
} from "./_components/AssetSummaryBar";
import {
  AssetFilterBar,
  type AssetFilterState,
  EMPTY_ASSET_FILTERS,
  countActiveAssetFilters,
} from "./_components/AssetFilterBar";
import { AssetCard } from "./_components/AssetCard";
import { AssetDetailPanel } from "./_components/AssetDetailPanel";
import { AddAssetDialog } from "./_components/AddAssetDialog";

// ─── Constants ────────────────────────────────────────────────────────────────

const FIRM_ID = "current";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AssetsPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);

  // ─── Data fetching ──────────────────────────────────────────────────────────
  const {
    data: assetsData,
    isLoading,
    error,
  } = useAssets(FIRM_ID, matterId, { per_page: 200 });
  const { data: entitiesData } = useEntities(FIRM_ID, matterId);

  const allAssets = assetsData?.data ?? [];
  const entities = entitiesData ?? [];

  // ─── UI state ───────────────────────────────────────────────────────────────
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<AssetFilterState>(EMPTY_ASSET_FILTERS);
  const [detailAssetId, setDetailAssetId] = useState<string | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  // ─── Filter logic ───────────────────────────────────────────────────────────
  const filteredAssets = useMemo(() => {
    let result = allAssets;

    if (filters.assetTypes.length > 0) {
      result = result.filter((a) => filters.assetTypes.includes(a.asset_type));
    }
    if (filters.ownershipType) {
      result = result.filter((a) => a.ownership_type === filters.ownershipType);
    }
    if (filters.transferMechanism) {
      result = result.filter(
        (a) => a.transfer_mechanism === filters.transferMechanism,
      );
    }
    if (filters.status) {
      result = result.filter((a) => a.status === filters.status);
    }
    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          (a.institution && a.institution.toLowerCase().includes(q)),
      );
    }

    return result;
  }, [allAssets, filters]);

  const activeFilterCount = countActiveAssetFilters(filters);

  // ─── Render ─────────────────────────────────────────────────────────────────
  if (isLoading) {
    return <LoadingState variant="cards" />;
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-danger">Failed to load assets.</p>
        <p className="text-sm text-muted-foreground mt-1">
          Please try refreshing the page.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <PageHeader
        title="Asset Registry"
        actions={
          <div className="flex items-center gap-2">
            {/* Filter toggle */}
            <Button
              variant={showFilters ? "outline" : "ghost"}
              size="sm"
              onClick={() => setShowFilters((v) => !v)}
              className="relative"
            >
              <Filter className="size-4 mr-1" />
              Filters
              {activeFilterCount > 0 && (
                <Badge
                  variant="default"
                  className="ml-1.5 size-5 p-0 flex items-center justify-center text-[10px]"
                >
                  {activeFilterCount}
                </Badge>
              )}
            </Button>

            {/* Add asset */}
            <Button size="sm" onClick={() => setAddDialogOpen(true)}>
              <Plus className="size-4 mr-1" />
              Add Asset
            </Button>
          </div>
        }
      />

      {/* Summary bar */}
      {allAssets.length > 0 && <AssetSummaryBar assets={allAssets} />}

      {/* Filter panel */}
      {showFilters && (
        <AssetFilterBar filters={filters} onChange={setFilters} />
      )}

      {/* Count */}
      {allAssets.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {filteredAssets.length} asset{filteredAssets.length !== 1 ? "s" : ""}
          {activeFilterCount > 0 && ` (filtered from ${allAssets.length})`}
        </p>
      )}

      {/* Asset grid */}
      {filteredAssets.length === 0 && allAssets.length > 0 ? (
        <EmptyState
          title="No assets match filters"
          description="Try adjusting your filters to see more assets."
          action={
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setFilters(EMPTY_ASSET_FILTERS);
                setShowFilters(false);
              }}
            >
              Clear filters
            </Button>
          }
        />
      ) : filteredAssets.length === 0 ? (
        <EmptyState
          title="No assets yet"
          description="Start building the estate inventory by adding assets."
          action={
            <Button size="sm" onClick={() => setAddDialogOpen(true)}>
              <Plus className="size-4 mr-1" />
              Add Asset
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredAssets.map((asset) => (
            <AssetCard
              key={asset.id}
              asset={asset}
              onClick={() => setDetailAssetId(asset.id)}
            />
          ))}
        </div>
      )}

      {/* Asset detail side panel */}
      <Sheet
        open={!!detailAssetId}
        onOpenChange={(open) => {
          if (!open) setDetailAssetId(null);
        }}
      >
        <SheetContent side="right" className="w-full sm:max-w-lg p-0">
          {detailAssetId && (
            <AssetDetailPanel
              assetId={detailAssetId}
              firmId={FIRM_ID}
              matterId={matterId}
              assets={allAssets}
              entities={entities}
              onClose={() => setDetailAssetId(null)}
            />
          )}
        </SheetContent>
      </Sheet>

      {/* Add asset dialog */}
      <AddAssetDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        firmId={FIRM_ID}
        matterId={matterId}
        entities={entities}
      />
    </div>
  );
}
