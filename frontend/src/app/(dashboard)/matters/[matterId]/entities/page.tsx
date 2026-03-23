"use client";

import { use, useState, useCallback } from "react";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
} from "@/components/ui/sheet";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import { useEntityMap, useEntities } from "@/hooks";
import type { Entity } from "@/lib/types";

import { EntityMapView } from "./_components/EntityMapView";
import { EntityListTable } from "./_components/EntityListTable";
import { EntityDetailPanel } from "./_components/EntityDetailPanel";
import { CreateEntityDialog } from "./_components/CreateEntityDialog";

// ─── Constants ────────────────────────────────────────────────────────────────

const FIRM_ID = "current";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function EntitiesPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);
  const router = useRouter();

  // ─── Data fetching ──────────────────────────────────────────────────────────
  const {
    data: entityMap,
    isLoading: mapLoading,
    error: mapError,
  } = useEntityMap(FIRM_ID, matterId);
  const {
    data: entities,
    isLoading: entitiesLoading,
  } = useEntities(FIRM_ID, matterId);

  // ─── UI state ───────────────────────────────────────────────────────────────
  const [detailEntity, setDetailEntity] = useState<Entity | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  const isLoading = mapLoading || entitiesLoading;

  // ─── Handlers ───────────────────────────────────────────────────────────────
  const handleEntityClick = useCallback(
    (entityId: string) => {
      const entity = (entities ?? []).find((e) => e.id === entityId);
      if (entity) setDetailEntity(entity);
    },
    [entities],
  );

  const handleAssetClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    (_assetId: string) => {
      router.push(`/matters/${matterId}/assets`);
    },
    [router, matterId],
  );

  // ─── Render ─────────────────────────────────────────────────────────────────
  if (isLoading) {
    return <LoadingState variant="cards" />;
  }

  if (mapError) {
    return (
      <div className="py-12 text-center">
        <p className="text-danger">Failed to load entity map.</p>
        <p className="text-sm text-muted-foreground mt-1">
          Please try refreshing the page.
        </p>
      </div>
    );
  }

  const mapEntities = entityMap?.entities ?? [];
  const unassignedAssets = entityMap?.unassigned_assets ?? [];
  const pourOverCandidates = entityMap?.pour_over_candidates ?? [];
  const fundingSummary = entityMap?.funding_summary ?? [];
  const allEntities = entities ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Entity Map"
        subtitle="Trust, LLC, and entity ownership structure"
        actions={
          <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="size-4 mr-1" />
            Add Entity
          </Button>
        }
      />

      {/* Entity Map Visualization */}
      <EntityMapView
        entities={mapEntities}
        unassignedAssets={unassignedAssets}
        pourOverCandidates={pourOverCandidates}
        fundingSummary={fundingSummary}
        onEntityClick={handleEntityClick}
        onAssetClick={handleAssetClick}
      />

      {/* Entity List Table */}
      {allEntities.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-foreground mb-3">
            All Entities
          </h2>
          <EntityListTable
            entities={allEntities}
            onEntityClick={handleEntityClick}
          />
        </div>
      )}

      {/* Entity Detail Side Panel */}
      <Sheet
        open={!!detailEntity}
        onOpenChange={(open) => {
          if (!open) setDetailEntity(null);
        }}
      >
        <SheetContent side="right" className="w-full sm:max-w-lg p-0">
          {detailEntity && (
            <EntityDetailPanel
              entity={detailEntity}
              firmId={FIRM_ID}
              matterId={matterId}
              onClose={() => setDetailEntity(null)}
              onAssetClick={handleAssetClick}
            />
          )}
        </SheetContent>
      </Sheet>

      {/* Create Entity Dialog */}
      <CreateEntityDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        firmId={FIRM_ID}
        matterId={matterId}
        unassignedAssets={unassignedAssets}
      />
    </div>
  );
}
