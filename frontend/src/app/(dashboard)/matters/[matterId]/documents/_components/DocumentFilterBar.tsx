"use client";

import { useState } from "react";
import { Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DOC_TYPE_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DocFilterState {
  docType: string | null;
  confirmationStatus: "all" | "confirmed" | "ai_suggested" | "unclassified";
  search: string;
}

export const EMPTY_DOC_FILTERS: DocFilterState = {
  docType: null,
  confirmationStatus: "all",
  search: "",
};

export function countActiveDocFilters(f: DocFilterState): number {
  let n = 0;
  if (f.docType) n++;
  if (f.confirmationStatus !== "all") n++;
  if (f.search) n++;
  return n;
}

// ─── Component ────────────────────────────────────────────────────────────────

interface DocumentFilterBarProps {
  filters: DocFilterState;
  onChange: (filters: DocFilterState) => void;
}

export function DocumentFilterBar({ filters, onChange }: DocumentFilterBarProps) {
  const [searchInput, setSearchInput] = useState(filters.search);

  const update = (patch: Partial<DocFilterState>) => {
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
          placeholder="Search by filename..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={handleSearchKeyDown}
          onBlur={handleSearchBlur}
          className="pl-9"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Document type */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1.5">Document Type</p>
          <select
            value={filters.docType ?? ""}
            onChange={(e) => update({ docType: e.target.value || null })}
            className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
          >
            <option value="">All types</option>
            {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>

        {/* Confirmation status */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1.5">Classification Status</p>
          <div className="flex flex-wrap gap-1.5">
            {(
              [
                { key: "all", label: "All" },
                { key: "confirmed", label: "Confirmed" },
                { key: "ai_suggested", label: "AI Suggested" },
                { key: "unclassified", label: "Unclassified" },
              ] as const
            ).map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => update({ confirmationStatus: key })}
                className={cn(
                  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer",
                  filters.confirmationStatus === key
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-surface text-muted-foreground hover:border-primary/30 hover:text-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Clear */}
      <div className="flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            onChange(EMPTY_DOC_FILTERS);
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
