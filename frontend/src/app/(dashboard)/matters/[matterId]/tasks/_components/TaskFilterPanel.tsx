"use client";

import { useState, useCallback } from "react";
import { Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  TASK_PHASE_LABELS,
  TASK_STATUS_LABELS,
  TASK_PRIORITY_LABELS,
} from "@/lib/constants";
import type { Stakeholder, TaskPhase, TaskStatus, TaskPriority } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TaskFilterState {
  phases: TaskPhase[];
  statuses: TaskStatus[];
  priorities: TaskPriority[];
  assignedTo: string | null;
  dueDateFrom: string;
  dueDateTo: string;
  search: string;
}

export const EMPTY_FILTERS: TaskFilterState = {
  phases: [],
  statuses: [],
  priorities: [],
  assignedTo: null,
  dueDateFrom: "",
  dueDateTo: "",
  search: "",
};

export function countActiveFilters(f: TaskFilterState): number {
  let n = 0;
  if (f.phases.length) n++;
  if (f.statuses.length) n++;
  if (f.priorities.length) n++;
  if (f.assignedTo) n++;
  if (f.dueDateFrom || f.dueDateTo) n++;
  if (f.search) n++;
  return n;
}

// ─── Chip Select ──────────────────────────────────────────────────────────────

function ChipSelect<T extends string>({
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
      selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key],
    );
  };

  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground mb-2">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(options).map(([key, label]) => {
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
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Filter Panel ─────────────────────────────────────────────────────────────

interface TaskFilterPanelProps {
  filters: TaskFilterState;
  onChange: (filters: TaskFilterState) => void;
  stakeholders: Stakeholder[];
}

export function TaskFilterPanel({ filters, onChange, stakeholders }: TaskFilterPanelProps) {
  const [searchInput, setSearchInput] = useState(filters.search);

  const update = useCallback(
    (patch: Partial<TaskFilterState>) => {
      onChange({ ...filters, ...patch });
    },
    [filters, onChange],
  );

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      update({ search: searchInput });
    }
  };

  const handleSearchBlur = () => {
    if (searchInput !== filters.search) {
      update({ search: searchInput });
    }
  };

  return (
    <div className="space-y-4 rounded-lg border border-border bg-card p-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          placeholder="Search tasks by title or description..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={handleSearchKeyDown}
          onBlur={handleSearchBlur}
          className="pl-9"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Phase */}
        <ChipSelect<TaskPhase>
          label="Phase"
          options={TASK_PHASE_LABELS}
          selected={filters.phases}
          onChange={(phases) => update({ phases })}
        />

        {/* Status */}
        <ChipSelect<TaskStatus>
          label="Status"
          options={TASK_STATUS_LABELS}
          selected={filters.statuses}
          onChange={(statuses) => update({ statuses })}
        />

        {/* Priority */}
        <ChipSelect<TaskPriority>
          label="Priority"
          options={TASK_PRIORITY_LABELS}
          selected={filters.priorities}
          onChange={(priorities) => update({ priorities })}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Assigned to */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">Assigned to</p>
          <select
            value={filters.assignedTo ?? ""}
            onChange={(e) => update({ assignedTo: e.target.value || null })}
            className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
          >
            <option value="">All</option>
            <option value="__unassigned__">Unassigned</option>
            {stakeholders.map((s) => (
              <option key={s.id} value={s.id}>
                {s.full_name}
              </option>
            ))}
          </select>
        </div>

        {/* Due date range */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">Due date range</p>
          <div className="flex items-center gap-2">
            <Input
              type="date"
              value={filters.dueDateFrom}
              onChange={(e) => update({ dueDateFrom: e.target.value })}
              className="flex-1 text-xs"
            />
            <span className="text-muted-foreground text-xs">to</span>
            <Input
              type="date"
              value={filters.dueDateTo}
              onChange={(e) => update({ dueDateTo: e.target.value })}
              className="flex-1 text-xs"
            />
          </div>
        </div>

        {/* Clear */}
        <div className="flex items-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              onChange(EMPTY_FILTERS);
              setSearchInput("");
            }}
            className="text-muted-foreground"
          >
            <X className="size-3.5 mr-1" />
            Clear filters
          </Button>
        </div>
      </div>
    </div>
  );
}
