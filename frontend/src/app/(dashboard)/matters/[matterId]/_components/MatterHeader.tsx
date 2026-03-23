"use client";

import { useState } from "react";
import { Check, MoreHorizontal, Pause, X, Archive, Pencil } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { useUpdateMatter, useCloseMatter } from "@/hooks";
import { ESTATE_TYPE_LABELS } from "@/lib/constants";
import type { Matter, MatterPhase } from "@/lib/types";

const PHASES: { key: MatterPhase; label: string }[] = [
  { key: "immediate", label: "Immediate" },
  { key: "administration", label: "Administration" },
  { key: "distribution", label: "Distribution" },
  { key: "closing", label: "Closing" },
];

function getPhaseIndex(phase: MatterPhase): number {
  return PHASES.findIndex((p) => p.key === phase);
}

interface MatterHeaderProps {
  matter: Matter;
  firmId: string;
}

export function MatterHeader({ matter, firmId }: MatterHeaderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(matter.title);
  const updateMatter = useUpdateMatter(firmId, matter.id);
  const closeMatter = useCloseMatter(firmId, matter.id);

  const currentPhaseIndex = getPhaseIndex(matter.phase);

  const handleSaveTitle = async () => {
    if (editTitle.trim() && editTitle !== matter.title) {
      await updateMatter.mutateAsync({ title: editTitle.trim() });
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSaveTitle();
    if (e.key === "Escape") {
      setEditTitle(matter.title);
      setIsEditing(false);
    }
  };

  const handleStatusChange = async (status: "active" | "on_hold") => {
    await updateMatter.mutateAsync({ status });
  };

  const estateLabel =
    ESTATE_TYPE_LABELS[matter.estate_type]?.label ?? matter.estate_type;

  const dateOfDeath = matter.date_of_death
    ? new Date(matter.date_of_death).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  return (
    <div className="space-y-4">
      {/* Title row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="flex items-center gap-2">
              <Input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={handleSaveTitle}
                className="text-2xl font-medium h-auto py-1 px-2"
                autoFocus
              />
              <Button size="icon" variant="ghost" onClick={handleSaveTitle}>
                <Check className="size-4" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => {
                  setEditTitle(matter.title);
                  setIsEditing(false);
                }}
              >
                <X className="size-4" />
              </Button>
            </div>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="group flex items-center gap-2 text-left"
            >
              <h1 className="text-2xl font-medium tracking-tight text-foreground">
                {matter.title}
              </h1>
              <Pencil className="size-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={matter.status} />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onClick={() => setIsEditing(true)}>
                <Pencil className="size-4" />
                Edit Title
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {matter.status === "active" && (
                <DropdownMenuItem onClick={() => handleStatusChange("on_hold")}>
                  <Pause className="size-4" />
                  Put on Hold
                </DropdownMenuItem>
              )}
              {matter.status === "on_hold" && (
                <DropdownMenuItem onClick={() => handleStatusChange("active")}>
                  <Check className="size-4" />
                  Resume Matter
                </DropdownMenuItem>
              )}
              {matter.status !== "closed" && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => closeMatter.mutate()}
                    className="text-danger"
                  >
                    <Archive className="size-4" />
                    Close Matter
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Metadata chips */}
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{matter.decedent_name}</Badge>
        {dateOfDeath && (
          <Badge variant="secondary">d. {dateOfDeath}</Badge>
        )}
        <Badge variant="secondary">{matter.jurisdiction_state}</Badge>
        <Badge variant="secondary">{estateLabel}</Badge>
      </div>

      {/* Phase indicator */}
      <div className="flex items-center gap-1">
        {PHASES.map((phase, i) => {
          const isCompleted = i < currentPhaseIndex;
          const isCurrent = i === currentPhaseIndex;

          return (
            <div key={phase.key} className="flex items-center gap-1 flex-1">
              {i > 0 && (
                <div
                  className={`h-px flex-1 transition-colors ${
                    isCompleted ? "bg-primary" : "bg-border"
                  }`}
                />
              )}
              <div className="flex items-center gap-1.5">
                <div
                  className={`flex size-6 items-center justify-center rounded-full text-[10px] font-medium transition-colors ${
                    isCompleted
                      ? "bg-primary text-primary-foreground"
                      : isCurrent
                        ? "bg-gold text-primary ring-2 ring-gold/20"
                        : "bg-surface-elevated text-muted-foreground"
                  }`}
                >
                  {isCompleted ? (
                    <Check className="size-3" />
                  ) : (
                    i + 1
                  )}
                </div>
                <span
                  className={`text-xs whitespace-nowrap ${
                    isCurrent
                      ? "font-medium text-foreground"
                      : isCompleted
                        ? "text-foreground"
                        : "text-muted-foreground"
                  }`}
                >
                  {phase.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
