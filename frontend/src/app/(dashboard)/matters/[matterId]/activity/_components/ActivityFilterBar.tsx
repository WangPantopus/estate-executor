"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Stakeholder } from "@/lib/types";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ActivityFilterState {
  entityType: string;
  action: string;
  actorId: string;
  dateFrom: string;
  dateTo: string;
}

export const EMPTY_ACTIVITY_FILTERS: ActivityFilterState = {
  entityType: "",
  action: "",
  actorId: "",
  dateFrom: "",
  dateTo: "",
};

export function hasActiveFilters(f: ActivityFilterState): boolean {
  return !!(f.entityType || f.action || f.actorId || f.dateFrom || f.dateTo);
}

const ENTITY_TYPES = [
  { value: "", label: "All" },
  { value: "task", label: "Tasks" },
  { value: "asset", label: "Assets" },
  { value: "document", label: "Documents" },
  { value: "stakeholder", label: "Stakeholders" },
  { value: "deadline", label: "Deadlines" },
  { value: "communication", label: "Communications" },
  { value: "matter", label: "Matter" },
  { value: "entity", label: "Entities" },
];

const ACTIONS = [
  { value: "", label: "All actions" },
  { value: "created", label: "Created" },
  { value: "updated", label: "Updated" },
  { value: "completed", label: "Completed" },
  { value: "uploaded", label: "Uploaded" },
  { value: "classified", label: "Classified" },
  { value: "assigned", label: "Assigned" },
  { value: "waived", label: "Waived" },
  { value: "deleted", label: "Deleted" },
  { value: "invited", label: "Invited" },
];

// ─── Component ────────────────────────────────────────────────────────────────

interface ActivityFilterBarProps {
  filters: ActivityFilterState;
  onChange: (filters: ActivityFilterState) => void;
  stakeholders: Stakeholder[];
}

export function ActivityFilterBar({
  filters,
  onChange,
  stakeholders,
}: ActivityFilterBarProps) {
  const update = (patch: Partial<ActivityFilterState>) => {
    onChange({ ...filters, ...patch });
  };

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-card p-4">
      {/* Entity type */}
      <div className="min-w-[130px]">
        <label className="text-xs font-medium text-muted-foreground mb-1 block">Type</label>
        <select
          value={filters.entityType}
          onChange={(e) => update({ entityType: e.target.value })}
          className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
        >
          {ENTITY_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>

      {/* Action */}
      <div className="min-w-[130px]">
        <label className="text-xs font-medium text-muted-foreground mb-1 block">Action</label>
        <select
          value={filters.action}
          onChange={(e) => update({ action: e.target.value })}
          className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
        >
          {ACTIONS.map((a) => (
            <option key={a.value} value={a.value}>{a.label}</option>
          ))}
        </select>
      </div>

      {/* Actor */}
      <div className="min-w-[150px]">
        <label className="text-xs font-medium text-muted-foreground mb-1 block">Actor</label>
        <select
          value={filters.actorId}
          onChange={(e) => update({ actorId: e.target.value })}
          className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
        >
          <option value="">All actors</option>
          <option value="__system__">System</option>
          <option value="__ai__">AI</option>
          {stakeholders.map((s) => (
            <option key={s.id} value={s.id}>{s.full_name}</option>
          ))}
        </select>
      </div>

      {/* Date range */}
      <div>
        <label className="text-xs font-medium text-muted-foreground mb-1 block">From</label>
        <Input
          type="date"
          value={filters.dateFrom}
          onChange={(e) => update({ dateFrom: e.target.value })}
          className="h-9 w-[140px] text-xs"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-muted-foreground mb-1 block">To</label>
        <Input
          type="date"
          value={filters.dateTo}
          onChange={(e) => update({ dateTo: e.target.value })}
          className="h-9 w-[140px] text-xs"
        />
      </div>

      {/* Clear */}
      {hasActiveFilters(filters) && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onChange(EMPTY_ACTIVITY_FILTERS)}
          className="text-muted-foreground h-9"
        >
          <X className="size-3.5 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );
}
