"use client";

import React from "react";
import {
  AlertTriangle,
  Shield,
  Eye,
  Users,
  User,
  CheckCircle2,
  Clock,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { STAKEHOLDER_ROLE_LABELS } from "@/lib/constants";
import { useAcknowledgeCommunication, useUpdateDisputeStatus } from "@/hooks";
import type { CommunicationResponse, CommunicationType, DisputeStatus, Stakeholder } from "@/lib/types";

// ─── Constants ────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<CommunicationType, string> = {
  message: "Message",
  milestone_notification: "Milestone Update",
  distribution_notice: "Distribution Notice",
  document_request: "Document Request",
  dispute_flag: "Dispute Flag",
};

const VISIBILITY_CONFIG: Record<string, { icon: React.ReactNode; label: string }> = {
  all_stakeholders: { icon: <Users className="size-3.5" />, label: "Visible to all stakeholders" },
  professionals_only: { icon: <Shield className="size-3.5" />, label: "Professionals only" },
  specific: { icon: <Eye className="size-3.5" />, label: "Specific recipients" },
};

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// ─── Component ────────────────────────────────────────────────────────────────

interface MessageDetailProps {
  communication: CommunicationResponse;
  firmId: string;
  matterId: string;
  stakeholders: Stakeholder[];
  currentUserId: string | null;
}

const DISPUTE_STATUS_LABELS: Record<string, string> = {
  open: "Open",
  under_review: "Under Review",
  resolved: "Resolved",
};

const DISPUTE_STATUS_COLORS: Record<string, string> = {
  open: "bg-red-50 text-red-700 border-red-200",
  under_review: "bg-amber-50 text-amber-700 border-amber-200",
  resolved: "bg-green-50 text-green-700 border-green-200",
};

export function MessageDetail({
  communication: comm,
  firmId,
  matterId,
  stakeholders,
  currentUserId,
}: MessageDetailProps) {
  const acknowledgeMutation = useAcknowledgeCommunication(firmId, matterId);
  const disputeMutation = useUpdateDisputeStatus(firmId, matterId);
  const [resolutionNote, setResolutionNote] = React.useState("");

  const isDispute = comm.type === "dispute_flag";
  const isDistNotice = comm.type === "distribution_notice";
  const visConfig = VISIBILITY_CONFIG[comm.visibility];

  // Find sender stakeholder for role info
  const sender = stakeholders.find((s) => s.id === comm.sender_id);

  // Check if current user has already acknowledged
  const currentStakeholder = stakeholders.find((s) => s.user_id === currentUserId);
  const hasAcknowledged = currentStakeholder
    ? comm.acknowledged_by.includes(currentStakeholder.id)
    : false;

  const handleAcknowledge = () => {
    acknowledgeMutation.mutate(comm.id);
  };

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-5">
        {/* Dispute flag warning banner with status */}
        {isDispute && (
          <div className="rounded-lg border-2 border-warning bg-warning-light/30 p-4 flex items-start gap-3">
            <AlertTriangle className="size-5 text-warning shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-warning">Dispute Flag</p>
                {comm.dispute_status && (
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border ${DISPUTE_STATUS_COLORS[comm.dispute_status] || DISPUTE_STATUS_COLORS.open}`}>
                    {DISPUTE_STATUS_LABELS[comm.dispute_status] || comm.dispute_status}
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {comm.dispute_status === "resolved"
                  ? "This dispute has been resolved."
                  : comm.dispute_status === "under_review"
                    ? "This dispute is currently under review."
                    : "A stakeholder has flagged a dispute. Review and address promptly."}
              </p>
              {comm.disputed_entity_type && (
                <p className="text-xs text-muted-foreground mt-1">
                  Disputed {comm.disputed_entity_type}: <span className="font-mono text-[10px]">{comm.disputed_entity_id}</span>
                </p>
              )}
              {comm.dispute_status === "resolved" && comm.dispute_resolution_note && (
                <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-800">
                  <p className="font-medium mb-0.5">Resolution Note:</p>
                  <p>{comm.dispute_resolution_note}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Header */}
        <div>
          {/* Type badge */}
          <Badge
            variant={isDispute ? "warning" : "muted"}
            className="text-[10px] mb-2"
          >
            {TYPE_LABELS[comm.type]}
          </Badge>

          {/* Subject */}
          <h2 className="text-lg font-medium text-foreground">
            {comm.subject || "(No subject)"}
          </h2>

          {/* Sender info */}
          <div className="flex items-center gap-3 mt-3">
            <div className="flex items-center justify-center size-9 rounded-full bg-surface-elevated text-muted-foreground">
              <User className="size-4" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">{comm.sender_name}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {sender && (
                  <span>{STAKEHOLDER_ROLE_LABELS[sender.role] ?? sender.role}</span>
                )}
                <span>{formatDateTime(comm.created_at)}</span>
              </div>
            </div>
          </div>

          {/* Visibility indicator */}
          {visConfig && (
            <div className="flex items-center gap-1.5 mt-3 text-xs text-muted-foreground">
              {visConfig.icon}
              <span>{visConfig.label}</span>
            </div>
          )}
        </div>

        <Separator />

        {/* Body */}
        <div className="prose prose-sm max-w-none text-foreground">
          <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {comm.body}
          </div>
        </div>

        {/* Distribution notice acknowledgment tracker */}
        {isDistNotice && (
          <>
            <Separator />
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-3">
                Acknowledgment Tracker
              </h3>
              <div className="space-y-2">
                {stakeholders
                  .filter((s) => s.role === "beneficiary" || s.role === "executor_trustee")
                  .map((s) => {
                    const acked = comm.acknowledged_by.includes(s.id);
                    return (
                      <div
                        key={s.id}
                        className="flex items-center justify-between rounded-md bg-surface-elevated px-3 py-2"
                      >
                        <div className="flex items-center gap-2">
                          <div className="flex items-center justify-center size-7 rounded-full bg-card text-muted-foreground">
                            <User className="size-3.5" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-foreground">{s.full_name}</p>
                            <p className="text-xs text-muted-foreground capitalize">
                              {STAKEHOLDER_ROLE_LABELS[s.role] ?? s.role}
                            </p>
                          </div>
                        </div>
                        {acked ? (
                          <Badge variant="success" className="text-[10px]">
                            <CheckCircle2 className="size-3 mr-0.5" />
                            Acknowledged
                          </Badge>
                        ) : (
                          <Badge variant="muted" className="text-[10px]">
                            <Clock className="size-3 mr-0.5" />
                            Pending
                          </Badge>
                        )}
                      </div>
                    );
                  })}
              </div>

              {/* Acknowledge button for current user */}
              {currentStakeholder && !hasAcknowledged && (
                <Button
                  className="mt-3 w-full"
                  onClick={handleAcknowledge}
                  disabled={acknowledgeMutation.isPending}
                >
                  {acknowledgeMutation.isPending ? (
                    <Loader2 className="size-4 mr-1 animate-spin" />
                  ) : (
                    <CheckCircle2 className="size-4 mr-1" />
                  )}
                  Acknowledge Receipt
                </Button>
              )}
              {hasAcknowledged && (
                <p className="text-xs text-success mt-2 text-center">
                  You have acknowledged this notice.
                </p>
              )}
            </div>
          </>
        )}

        {/* Dispute resolution controls (matter admins only) */}
        {isDispute && comm.dispute_status !== "resolved" && currentStakeholder?.role === "matter_admin" && (
          <>
            <Separator />
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-3">
                Dispute Resolution
              </h3>
              <textarea
                className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 min-h-[80px] resize-y"
                placeholder="Enter a note explaining the status change..."
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
              />
              <div className="flex gap-2 mt-3">
                {comm.dispute_status !== "under_review" && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    disabled={!resolutionNote.trim() || disputeMutation.isPending}
                    onClick={() => {
                      disputeMutation.mutate(
                        { commId: comm.id, data: { status: "under_review", resolution_note: resolutionNote.trim() } },
                        { onSuccess: () => setResolutionNote("") },
                      );
                    }}
                  >
                    {disputeMutation.isPending ? (
                      <Loader2 className="size-4 mr-1 animate-spin" />
                    ) : (
                      <Clock className="size-4 mr-1" />
                    )}
                    Mark Under Review
                  </Button>
                )}
                <Button
                  size="sm"
                  className="flex-1"
                  disabled={!resolutionNote.trim() || disputeMutation.isPending}
                  onClick={() => {
                    disputeMutation.mutate(
                      { commId: comm.id, data: { status: "resolved", resolution_note: resolutionNote.trim() } },
                      { onSuccess: () => setResolutionNote("") },
                    );
                  }}
                >
                  {disputeMutation.isPending ? (
                    <Loader2 className="size-4 mr-1 animate-spin" />
                  ) : (
                    <CheckCircle2 className="size-4 mr-1" />
                  )}
                  Mark Resolved
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </ScrollArea>
  );
}
