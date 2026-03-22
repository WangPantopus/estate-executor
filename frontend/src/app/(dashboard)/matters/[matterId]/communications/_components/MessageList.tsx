"use client";

import { useMemo } from "react";
import {
  MessageSquare,
  Flag,
  Bell,
  FileText,
  AlertTriangle,
  UserCircle,
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import type { CommunicationResponse, CommunicationType, Stakeholder } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const TYPE_ICONS: Record<CommunicationType, React.ReactNode> = {
  message: <MessageSquare className="size-4" />,
  milestone_notification: <Bell className="size-4" />,
  distribution_notice: <FileText className="size-4" />,
  document_request: <FileText className="size-4" />,
  dispute_flag: <AlertTriangle className="size-4" />,
};

const TYPE_COLORS: Record<CommunicationType, string> = {
  message: "text-info",
  milestone_notification: "text-primary",
  distribution_notice: "text-success",
  document_request: "text-muted-foreground",
  dispute_flag: "text-danger",
};

type FilterTab = "all" | "message" | "milestone_notification" | "distribution_notice" | "dispute_flag";

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  }
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// ─── Component ────────────────────────────────────────────────────────────────

interface MessageListProps {
  communications: CommunicationResponse[];
  stakeholders: Stakeholder[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  activeTab: FilterTab;
  onTabChange: (tab: FilterTab) => void;
}

export type { FilterTab };

export function MessageList({
  communications,
  stakeholders,
  selectedId,
  onSelect,
  activeTab,
  onTabChange,
}: MessageListProps) {
  const filtered = useMemo(() => {
    let result = communications;
    if (activeTab !== "all") {
      result = result.filter((c) => c.type === activeTab);
    }
    return result.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
  }, [communications, activeTab]);

  const tabCounts = useMemo(() => {
    const counts: Record<string, number> = { all: communications.length };
    for (const c of communications) {
      counts[c.type] = (counts[c.type] ?? 0) + 1;
    }
    return counts;
  }, [communications]);

  return (
    <div className="flex flex-col h-full border-r border-border">
      {/* Tabs */}
      <div className="px-3 pt-3 pb-2 border-b border-border shrink-0">
        <Tabs value={activeTab} onValueChange={(v) => onTabChange(v as FilterTab)}>
          <TabsList className="w-full h-8">
            <TabsTrigger value="all" className="text-xs flex-1">
              All
              {tabCounts.all > 0 && (
                <span className="ml-1 text-[10px] text-muted-foreground">{tabCounts.all}</span>
              )}
            </TabsTrigger>
            <TabsTrigger value="message" className="text-xs flex-1">Msgs</TabsTrigger>
            <TabsTrigger value="milestone_notification" className="text-xs flex-1">Miles.</TabsTrigger>
            <TabsTrigger value="distribution_notice" className="text-xs flex-1">Dist.</TabsTrigger>
            <TabsTrigger value="dispute_flag" className="text-xs flex-1">
              Disp.
              {(tabCounts.dispute_flag ?? 0) > 0 && (
                <Badge variant="danger" className="ml-1 size-4 p-0 flex items-center justify-center text-[9px]">
                  {tabCounts.dispute_flag}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Message items */}
      <ScrollArea className="flex-1">
        {filtered.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-sm text-muted-foreground">No messages</p>
          </div>
        ) : (
          <div className="py-1">
            {filtered.map((comm) => {
              const isSelected = comm.id === selectedId;
              const isDispute = comm.type === "dispute_flag";
              const isDistNotice = comm.type === "distribution_notice";
              const ackCount = comm.acknowledged_by.length;
              // Rough total recipients count — use stakeholders length as proxy
              const totalRecipients = stakeholders.length;

              return (
                <button
                  key={comm.id}
                  type="button"
                  onClick={() => onSelect(comm.id)}
                  className={cn(
                    "w-full text-left px-3 py-2.5 transition-colors",
                    isSelected
                      ? "bg-primary/5 border-l-2 border-l-primary"
                      : "hover:bg-surface-elevated border-l-2 border-l-transparent",
                    isDispute && !isSelected && "bg-danger-light/20",
                  )}
                >
                  <div className="flex items-start gap-2.5">
                    {/* Type icon */}
                    <span className={cn("mt-0.5 shrink-0", TYPE_COLORS[comm.type])}>
                      {TYPE_ICONS[comm.type]}
                    </span>

                    <div className="flex-1 min-w-0">
                      {/* Subject / first line */}
                      <p className="text-sm font-medium text-foreground truncate">
                        {comm.subject || comm.body.slice(0, 60)}
                      </p>

                      {/* Sender + time */}
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-muted-foreground truncate">
                          {comm.sender_name}
                        </span>
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          {formatTime(comm.created_at)}
                        </span>
                      </div>

                      {/* Distribution notice ack count */}
                      {isDistNotice && (
                        <div className="mt-1">
                          <Badge
                            variant={ackCount >= totalRecipients ? "success" : "warning"}
                            className="text-[10px]"
                          >
                            {ackCount}/{totalRecipients} acknowledged
                          </Badge>
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
