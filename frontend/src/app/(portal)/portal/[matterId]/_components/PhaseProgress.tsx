"use client";

import { cn } from "@/lib/utils";
import type { MatterPhase } from "@/lib/types";

const PHASES: { key: MatterPhase; label: string }[] = [
  { key: "immediate", label: "Initial Steps" },
  { key: "administration", label: "Administration" },
  { key: "distribution", label: "Distribution" },
  { key: "closing", label: "Closing" },
];

const PHASE_ORDER: Record<MatterPhase, number> = {
  immediate: 0,
  administration: 1,
  distribution: 2,
  closing: 3,
};

interface PhaseProgressProps {
  currentPhase: MatterPhase;
  completionPercentage: number;
}

export function PhaseProgress({
  currentPhase,
  completionPercentage,
}: PhaseProgressProps) {
  const currentIndex = PHASE_ORDER[currentPhase] ?? 0;

  return (
    <div className="rounded-xl border border-border bg-card p-6 sm:p-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          Estate Progress
        </h2>
        <span className="text-sm font-medium text-foreground">
          {completionPercentage}% complete
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-surface-elevated rounded-full mb-8 overflow-hidden">
        <div
          className="h-full bg-gold rounded-full transition-all duration-700 ease-out"
          style={{ width: `${Math.max(completionPercentage, 2)}%` }}
        />
      </div>

      {/* Phase stepper */}
      <div className="flex items-start justify-between">
        {PHASES.map((phase, i) => {
          const isComplete = i < currentIndex;
          const isCurrent = i === currentIndex;

          return (
            <div key={phase.key} className="flex flex-col items-center flex-1">
              {/* Dot */}
              <div className="relative flex items-center justify-center mb-2">
                <div
                  className={cn(
                    "size-3 rounded-full transition-colors",
                    isComplete && "bg-success",
                    isCurrent && "bg-gold ring-4 ring-gold/20",
                    !isComplete && !isCurrent && "bg-border",
                  )}
                />
                {/* Connecting line */}
                {i < PHASES.length - 1 && (
                  <div
                    className={cn(
                      "absolute left-1/2 top-1/2 -translate-y-1/2 h-0.5 w-full",
                      isComplete ? "bg-success" : "bg-border",
                    )}
                    style={{
                      width: "calc(100% + 2rem)",
                      left: "50%",
                    }}
                  />
                )}
              </div>
              {/* Label */}
              <span
                className={cn(
                  "text-xs text-center leading-tight",
                  isCurrent
                    ? "text-foreground font-medium"
                    : isComplete
                      ? "text-success"
                      : "text-muted-foreground",
                )}
              >
                {phase.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
