"use client";

import { DollarSign, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAcknowledgeCommunication, useCurrentUser } from "@/hooks";
import { useToast } from "@/components/layout/Toaster";
import type { CommunicationResponse } from "@/lib/types";

const FIRM_ID = "current";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

interface DistributionSummaryProps {
  communications: CommunicationResponse[];
  matterId: string;
}

export function DistributionSummary({
  communications,
  matterId,
}: DistributionSummaryProps) {
  const { data: currentUser } = useCurrentUser();
  const acknowledgeMutation = useAcknowledgeCommunication(FIRM_ID, matterId);
  const { toast } = useToast();

  const currentUserId = currentUser?.user_id ?? "";

  const handleAcknowledge = async (commId: string) => {
    try {
      await acknowledgeMutation.mutateAsync(commId);
      toast("success", "Distribution notice acknowledged.");
    } catch {
      toast("error", "Failed to acknowledge. Please try again.");
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card p-6 sm:p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex size-9 items-center justify-center rounded-lg bg-gold/10">
          <DollarSign className="size-4 text-gold" />
        </div>
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          Distribution Notices
        </h2>
      </div>

      <div className="space-y-4">
        {communications.map((comm) => {
          const isAcknowledged = comm.acknowledged_by?.includes(currentUserId);

          return (
            <div
              key={comm.id}
              className="rounded-lg border border-border p-4 sm:p-5 space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">
                    {comm.subject || "Distribution Notice"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {formatDate(comm.created_at)}
                  </p>
                </div>
                {isAcknowledged && (
                  <div className="flex items-center gap-1 shrink-0 text-success">
                    <CheckCircle2 className="size-4" />
                    <span className="text-xs font-medium">Acknowledged</span>
                  </div>
                )}
              </div>

              <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                {comm.body}
              </p>

              {!isAcknowledged && (
                <Button
                  size="sm"
                  onClick={() => handleAcknowledge(comm.id)}
                  disabled={acknowledgeMutation.isPending}
                  className="bg-gold hover:bg-gold-light text-primary"
                >
                  Acknowledge Receipt
                </Button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
