"use client";

import { CircleCheckBig, User, Phone } from "lucide-react";
import type { Stakeholder } from "@/lib/types";

interface InfoCardsProps {
  completionPercentage: number;
  leadProfessional: Stakeholder | null;
}

export function InfoCards({
  completionPercentage,
  leadProfessional,
}: InfoCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {/* Completion status */}
      <div className="rounded-xl border border-border bg-card p-5 sm:p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-success-light">
            <CircleCheckBig className="size-4 text-success" />
          </div>
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Progress
          </span>
        </div>
        <p className="text-2xl font-semibold text-foreground">
          {completionPercentage}%
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          Tasks completed
        </p>
      </div>

      {/* Your role */}
      <div className="rounded-xl border border-border bg-card p-5 sm:p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-info-light">
            <User className="size-4 text-info" />
          </div>
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Your Role
          </span>
        </div>
        <p className="text-2xl font-semibold text-foreground">Beneficiary</p>
        <p className="text-sm text-muted-foreground mt-1">
          You will receive updates as the estate progresses
        </p>
      </div>

      {/* Lead contact */}
      <div className="rounded-xl border border-border bg-card p-5 sm:p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gold/10">
            <Phone className="size-4 text-gold" />
          </div>
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Your Contact
          </span>
        </div>
        {leadProfessional ? (
          <>
            <p className="text-lg font-semibold text-foreground">
              {leadProfessional.full_name}
            </p>
            <p className="text-sm text-muted-foreground mt-0.5">
              {leadProfessional.relationship ?? "Estate Administrator"}
            </p>
            <p className="text-sm text-muted-foreground">
              {leadProfessional.email}
            </p>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            Contact information will appear here once assigned.
          </p>
        )}
      </div>
    </div>
  );
}
