"use client";

import { use, useState, useMemo, useCallback } from "react";
import {
  MessageSquare,
  Send,
  CheckCircle2,
  Clock,
  Bell,
  AlertTriangle,
} from "lucide-react";
import {
  useCommunications,
  useCreateCommunication,
  useAcknowledgeCommunication,
  useCurrentUser,
  useStakeholders,
} from "@/hooks";
import { LoadingState } from "@/components/layout/LoadingState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/layout/Toaster";
import { cn } from "@/lib/utils";
import type { CommunicationResponse, CommunicationType } from "@/lib/types";

const FIRM_ID = "current";

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    });
  }
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function getTypeIcon(type: CommunicationType) {
  switch (type) {
    case "milestone_notification":
      return Bell;
    case "distribution_notice":
      return CheckCircle2;
    case "dispute_flag":
      return AlertTriangle;
    default:
      return MessageSquare;
  }
}

function getTypeLabel(type: CommunicationType): string {
  switch (type) {
    case "milestone_notification":
      return "Milestone Update";
    case "distribution_notice":
      return "Distribution Notice";
    case "document_request":
      return "Document Request";
    case "dispute_flag":
      return "Dispute";
    default:
      return "Message";
  }
}

// ─── Compose Area ─────────────────────────────────────────────────────────────

function ComposeArea({
  matterId,
}: {
  matterId: string;
}) {
  const [body, setBody] = useState("");
  const createMutation = useCreateCommunication(FIRM_ID, matterId);
  const { toast } = useToast();

  const handleSend = async () => {
    const trimmed = body.trim();
    if (!trimmed) return;

    try {
      await createMutation.mutateAsync({
        type: "message",
        body: trimmed,
        visibility: "all_stakeholders",
      });
      setBody("");
      toast("success", "Message sent.");
    } catch {
      toast("error", "Failed to send message. Please try again.");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Write a message to your estate administrator..."
        className="min-h-[80px] resize-none border-0 bg-transparent p-0 text-sm focus-visible:ring-0 placeholder:text-muted-foreground/50"
      />
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
        <p className="text-xs text-muted-foreground hidden sm:block">
          Press Cmd+Enter to send
        </p>
        <Button
          size="sm"
          onClick={handleSend}
          disabled={!body.trim() || createMutation.isPending}
          className="bg-primary hover:bg-primary-light"
        >
          <Send className="size-4 mr-1.5" />
          Send Message
        </Button>
      </div>
    </div>
  );
}

// ─── Message Card ─────────────────────────────────────────────────────────────

function MessageCard({
  comm,
  matterId,
  currentUserId,
  stakeholderNames,
}: {
  comm: CommunicationResponse;
  matterId: string;
  currentUserId: string;
  stakeholderNames: Record<string, string>;
}) {
  const acknowledgeMutation = useAcknowledgeCommunication(FIRM_ID, matterId);
  const { toast } = useToast();

  const Icon = getTypeIcon(comm.type);
  const isDistributionNotice = comm.type === "distribution_notice";
  const isAcknowledged = comm.acknowledged_by?.includes(currentUserId);
  const senderName = stakeholderNames[comm.sender_id] ?? comm.sender_name ?? "Estate Team";
  const isFromCurrentUser = comm.sender_id === currentUserId;

  const handleAcknowledge = async () => {
    try {
      await acknowledgeMutation.mutateAsync(comm.id);
      toast("success", "Notice acknowledged.");
    } catch {
      toast("error", "Failed to acknowledge. Please try again.");
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl border p-4 sm:p-5 space-y-3 transition-colors",
        isDistributionNotice && !isAcknowledged
          ? "border-gold/40 bg-gold/5"
          : "border-border bg-card",
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={cn(
              "flex size-8 items-center justify-center rounded-full shrink-0",
              isFromCurrentUser
                ? "bg-info-light"
                : "bg-surface-elevated",
            )}
          >
            <Icon className="size-3.5 text-muted-foreground" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground">
              {senderName}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                {getTypeLabel(comm.type)}
              </span>
              <span className="text-xs text-muted-foreground/50">·</span>
              <span className="text-xs text-muted-foreground">
                {formatDate(comm.created_at)}
              </span>
            </div>
          </div>
        </div>

        {isDistributionNotice && isAcknowledged && (
          <div className="flex items-center gap-1 shrink-0 text-success">
            <CheckCircle2 className="size-3.5" />
            <span className="text-xs font-medium">Acknowledged</span>
          </div>
        )}
      </div>

      {/* Subject */}
      {comm.subject && (
        <p className="text-sm font-medium text-foreground">{comm.subject}</p>
      )}

      {/* Body */}
      <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
        {comm.body}
      </p>

      {/* Acknowledge button for distribution notices */}
      {isDistributionNotice && !isAcknowledged && (
        <div className="pt-1">
          <Button
            size="sm"
            onClick={handleAcknowledge}
            disabled={acknowledgeMutation.isPending}
            className="bg-gold hover:bg-gold-light text-primary"
          >
            <CheckCircle2 className="size-4 mr-1.5" />
            Acknowledge Receipt
          </Button>
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PortalMessagesPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);
  const { data: commsData, isLoading, error } = useCommunications(FIRM_ID, matterId);
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);
  const { data: currentUser } = useCurrentUser();

  const currentUserId = currentUser?.user_id ?? "";

  // Build stakeholder name lookup
  const stakeholderNames = useMemo(() => {
    const map: Record<string, string> = {};
    for (const s of stakeholdersData?.data ?? []) {
      map[s.id] = s.full_name;
      if (s.user_id) map[s.user_id] = s.full_name;
    }
    return map;
  }, [stakeholdersData]);

  // Filter communications visible to beneficiaries
  const communications = useMemo(() => {
    const all = commsData?.data ?? [];
    return all.filter((c) => c.visibility !== "professionals_only");
  }, [commsData]);

  if (isLoading) {
    return <LoadingState variant="list" />;
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-danger">Unable to load messages.</p>
          <p className="text-sm text-muted-foreground mt-2">
            Please try refreshing the page.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Sort: distribution notices needing acknowledgment first, then by date desc
  const sorted = [...communications].sort((a, b) => {
    const aIsUnacked =
      a.type === "distribution_notice" &&
      !a.acknowledged_by?.includes(currentUserId);
    const bIsUnacked =
      b.type === "distribution_notice" &&
      !b.acknowledged_by?.includes(currentUserId);
    if (aIsUnacked && !bIsUnacked) return -1;
    if (!aIsUnacked && bIsUnacked) return 1;
    return (
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-serif font-semibold text-foreground">
          Messages
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Stay in touch with your estate administrator.
        </p>
      </div>

      {/* Compose */}
      <ComposeArea matterId={matterId} />

      {/* Messages */}
      {sorted.length === 0 ? (
        <div className="rounded-xl border border-border bg-card py-16 text-center">
          <MessageSquare className="size-10 text-muted-foreground/30 mx-auto mb-4" />
          <p className="text-sm font-medium text-foreground">
            No messages yet
          </p>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
            Messages and updates from your estate administrator will appear
            here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map((comm) => (
            <MessageCard
              key={comm.id}
              comm={comm}
              matterId={matterId}
              currentUserId={currentUserId}
              stakeholderNames={stakeholderNames}
            />
          ))}
        </div>
      )}
    </div>
  );
}
