"use client";

import { useState, useEffect } from "react";
import { Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ASSET_TYPE_LABELS,
  OWNERSHIP_TYPE_LABELS,
  TRANSFER_MECHANISM_LABELS,
  ASSET_STATUS_LABELS,
} from "@/lib/constants";
import type { AssetType, OwnershipType, TransferMechanism, AssetStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AssetFilterState {
  assetTypes: AssetType[];
  ownershipType: OwnershipType | null;
  transferMechanism: TransferMechanism | null;
  status: AssetStatus | null;
  search: string;
}

export const EMPTY_ASSET_FILTERS: AssetFilterState = {
  assetTypes: [],
  ownershipType: null,
  transferMechanism: null,
  status: null,
  search: "",
};

export function countActiveAssetFilters(f: AssetFilterState): number {
  let n = 0;
  if (f.assetTypes.length) n++;
  if (f.ownershipType) n++;
  if (f.transferMechanism) n++;
  if (f.status) n++;
  if (f.search) n++;
  return n;
}

// ─── Chip Multi-Select ────────────────────────────────────────────────────────

function ChipMultiSelect<T extends string>({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: Record<string, string>;
  selected: T[];
  onChange: (val: T[]) => void;
}) {
  const toggle = (key: T) => {
    onChange(
      selected.includes(key)
        ? selected.filter((k) => k !== key)
        : [...selected, key],
    );
  };

  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(options).map(([key, lbl]) => {
          const active = selected.includes(key as T);
          return (
            <button
              key={key}
              type="button"
              onClick={() => toggle(key as T)}
              className={cn(
                "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer",
                active
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-surface text-muted-foreground hover:border-primary/30 hover:text-foreground",
              )}
            >
              {lbl}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Filter Bar ───────────────────────────────────────────────────────────────

interface AssetFilterBarProps {
  filters: AssetFilterState;
  onChange: (filters: AssetFilterState) => void;
}

export function AssetFilterBar({ filters, onChange }: AssetFilterBarProps) {
  const [searchInput, setSearchInput] = useState(filters.search);

  useEffect(() => {
    setSearchInput(filters.search); // eslint-disable-line react-hooks/set-state-in-effect -- sync local input from parent filter reset
  }, [filters.search]);

  const update = (patch: Partial<AssetFilterState>) => {
    onChange({ ...filters, ...patch });
  };

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") update({ search: searchInput });
  };

  const handleSearchBlur = () => {
    if (searchInput !== filters.search) update({ search: searchInput });
  };

  return (
    <div className="space-y-4 rounded-lg border border-border bg-card p-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          placeholder="Search by title or institution..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={handleSearchKeyDown}
          onBlur={handleSearchBlur}
          className="pl-9"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Asset type */}
        <ChipMultiSelect<AssetType>
          label="Asset Type"
          options={ASSET_TYPE_LABELS}
          selected={filters.assetTypes}
          onChange={(assetTypes) => update({ assetTypes })}
        />

        {/* Status */}
        <div className="space-y-4">
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1.5">Status</p>
            <select
              value={filters.status ?? ""}
              onChange={(e) => update({ status: (e.target.value || null) as AssetStatus | null })}
              className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
            >
              <option value="">All statuses</option>
              {Object.entries(ASSET_STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Ownership */}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5">Ownership</p>
              <select
                value={filters.ownershipType ?? ""}
                onChange={(e) => update({ ownershipType: (e.target.value || null) as OwnershipType | null })}
                className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
              >
                <option value="">All</option>
                {Object.entries(OWNERSHIP_TYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>

            {/* Transfer */}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5">Transfer</p>
              <select
                value={filters.transferMechanism ?? ""}
                onChange={(e) => update({ transferMechanism: (e.target.value || null) as TransferMechanism | null })}
                className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
              >
                <option value="">All</option>
                {Object.entries(TRANSFER_MECHANISM_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Clear */}
      <div className="flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            onChange(EMPTY_ASSET_FILTERS);
            setSearchInput("");
          }}
          className="text-muted-foreground"
        >
          <X className="size-3.5 mr-1" />
          Clear filters
        </Button>
      </div>
    </div>
  );
}
