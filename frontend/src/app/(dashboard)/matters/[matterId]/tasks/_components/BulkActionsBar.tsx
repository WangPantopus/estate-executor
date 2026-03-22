"use client";

import { X, UserPlus, ArrowRightLeft, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TASK_STATUS_LABELS, TASK_PRIORITY_LABELS } from "@/lib/constants";
import type { Stakeholder, TaskStatus, TaskPriority } from "@/lib/types";

interface BulkActionsBarProps {
  selectedCount: number;
  stakeholders: Stakeholder[];
  onClear: () => void;
  onBulkAssign: (stakeholderId: string) => void;
  onBulkStatusChange: (status: TaskStatus) => void;
  onBulkPriorityChange: (priority: TaskPriority) => void;
}

export function BulkActionsBar({
  selectedCount,
  stakeholders,
  onClear,
  onBulkAssign,
  onBulkStatusChange,
  onBulkPriorityChange,
}: BulkActionsBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-2.5">
      <span className="text-sm font-medium text-primary">
        {selectedCount} selected
      </span>

      <div className="h-4 w-px bg-border" />

      {/* Assign */}
      <Select onValueChange={onBulkAssign}>
        <SelectTrigger className="h-8 w-auto min-w-[130px] text-xs">
          <UserPlus className="size-3.5 mr-1" />
          <SelectValue placeholder="Assign to..." />
        </SelectTrigger>
        <SelectContent>
          {stakeholders.map((s) => (
            <SelectItem key={s.id} value={s.id}>
              {s.full_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Status */}
      <Select onValueChange={(val) => onBulkStatusChange(val as TaskStatus)}>
        <SelectTrigger className="h-8 w-auto min-w-[130px] text-xs">
          <ArrowRightLeft className="size-3.5 mr-1" />
          <SelectValue placeholder="Change status..." />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(TASK_STATUS_LABELS).map(([key, label]) => (
            <SelectItem key={key} value={key}>
              {label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Priority */}
      <Select onValueChange={(val) => onBulkPriorityChange(val as TaskPriority)}>
        <SelectTrigger className="h-8 w-auto min-w-[130px] text-xs">
          <AlertTriangle className="size-3.5 mr-1" />
          <SelectValue placeholder="Change priority..." />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(TASK_PRIORITY_LABELS).map(([key, label]) => (
            <SelectItem key={key} value={key}>
              {label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="ml-auto">
        <Button variant="ghost" size="sm" onClick={onClear} className="text-xs">
          <X className="size-3.5 mr-1" />
          Clear
        </Button>
      </div>
    </div>
  );
}
