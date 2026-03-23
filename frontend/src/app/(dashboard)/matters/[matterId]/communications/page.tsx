"use client";

import { use, useState, useMemo, useCallback } from "react";
import { Plus, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import { EmptyState } from "@/components/layout/EmptyState";
import {
  useCommunications,
  useStakeholders,
  useCurrentUser,
} from "@/hooks";

import { MessageList, type FilterTab } from "./_components/MessageList";
import { MessageDetail } from "./_components/MessageDetail";
import { ComposeMessage } from "./_components/ComposeMessage";

// ─── Constants ────────────────────────────────────────────────────────────────

const FIRM_ID = "current";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CommunicationsPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);

  // ─── Data fetching ──────────────────────────────────────────────────────────
  const {
    data: commsData,
    isLoading,
    error,
  } = useCommunications(FIRM_ID, matterId);
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);
  const { data: currentUser } = useCurrentUser();

  const allComms = commsData?.data ?? [];
  const stakeholders = stakeholdersData?.data ?? [];
  const currentUserId = currentUser?.user_id ?? null;

  // Filter by visibility based on current user's role
  const currentStakeholder = stakeholders.find((s) => s.user_id === currentUserId);
  const isBeneficiaryOrReadOnly =
    currentStakeholder?.role === "beneficiary" || currentStakeholder?.role === "read_only";
  const communications = useMemo(
    () =>
      isBeneficiaryOrReadOnly
        ? allComms.filter((c) => c.visibility !== "professionals_only")
        : allComms,
    [allComms, isBeneficiaryOrReadOnly],
  );

  // ─── UI state ───────────────────────────────────────────────────────────────
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [composeOpen, setComposeOpen] = useState(false);

  // Selected communication
  const selectedComm = useMemo(
    () => communications.find((c) => c.id === selectedId) ?? null,
    [communications, selectedId],
  );

  // Auto-select first message when none selected and messages exist
  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
  }, []);

  // ─── Render ─────────────────────────────────────────────────────────────────
  if (isLoading) {
    return <LoadingState variant="list" />;
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-danger">Failed to load communications.</p>
        <p className="text-sm text-muted-foreground mt-1">
          Please try refreshing the page.
        </p>
      </div>
    );
  }

  if (communications.length === 0) {
    return (
      <div className="space-y-4">
        <PageHeader
          title="Communications"
          actions={
            <Button size="sm" onClick={() => setComposeOpen(true)}>
              <Plus className="size-4 mr-1" />
              New Message
            </Button>
          }
        />
        <EmptyState
          icon={<MessageSquare className="size-12" />}
          title="No communications yet"
          description="Send a message, milestone update, or distribution notice to stakeholders."
          action={
            <Button size="sm" onClick={() => setComposeOpen(true)}>
              <Plus className="size-4 mr-1" />
              New Message
            </Button>
          }
        />
        <ComposeMessage
          open={composeOpen}
          onOpenChange={setComposeOpen}
          firmId={FIRM_ID}
          matterId={matterId}
          stakeholders={stakeholders}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Communications"
        actions={
          <Button size="sm" onClick={() => setComposeOpen(true)}>
            <Plus className="size-4 mr-1" />
            New Message
          </Button>
        }
      />

      {/* Split layout */}
      <div className="rounded-lg border border-border bg-card overflow-hidden flex" style={{ height: "calc(100vh - 220px)", minHeight: "500px" }}>
        {/* Left sidebar — message list */}
        <div className="w-full sm:w-[320px] lg:w-[360px] shrink-0">
          <MessageList
            communications={communications}
            stakeholders={stakeholders}
            selectedId={selectedId}
            onSelect={handleSelect}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />
        </div>

        {/* Right panel — message detail */}
        <div className="hidden sm:flex flex-1 border-l border-border">
          {selectedComm ? (
            <div className="flex-1">
              <MessageDetail
                communication={selectedComm}
                firmId={FIRM_ID}
                matterId={matterId}
                stakeholders={stakeholders}
                currentUserId={currentUserId}
              />
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageSquare className="size-10 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">
                  Select a message to view
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mobile: show detail as overlay when selected */}
      {selectedComm && (
        <div className="sm:hidden fixed inset-0 z-50 bg-card">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedId(null)}
            >
              Back
            </Button>
            <span className="text-sm font-medium text-foreground truncate">
              {selectedComm.subject || "Message"}
            </span>
            <div className="w-12" />
          </div>
          <MessageDetail
            communication={selectedComm}
            firmId={FIRM_ID}
            matterId={matterId}
            stakeholders={stakeholders}
            currentUserId={currentUserId}
          />
        </div>
      )}

      {/* Floating compose button (mobile) */}
      <Button
        size="icon"
        className="fixed bottom-6 right-6 size-12 rounded-full shadow-lg sm:hidden z-30"
        onClick={() => setComposeOpen(true)}
      >
        <Plus className="size-5" />
      </Button>

      {/* Compose dialog */}
      <ComposeMessage
        open={composeOpen}
        onOpenChange={setComposeOpen}
        firmId={FIRM_ID}
        matterId={matterId}
        stakeholders={stakeholders}
      />
    </div>
  );
}
