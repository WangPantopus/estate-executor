"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import {
  usePortalMessages,
  usePostPortalMessage,
  useAcknowledgeNotice,
} from "@/hooks/use-portal-queries";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  MessageSquare,
  Send,
  Bell,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const TYPE_CONFIG: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  distribution_notice: {
    label: "Distribution Notice",
    icon: Bell,
    color: "text-amber-600 bg-amber-50 border-amber-200",
  },
  milestone_notification: {
    label: "Milestone",
    icon: CheckCircle2,
    color: "text-emerald-600 bg-emerald-50 border-emerald-200",
  },
  message: {
    label: "Message",
    icon: MessageSquare,
    color: "text-blue-600 bg-blue-50 border-blue-200",
  },
};

export default function PortalMessagesPage() {
  const params = useParams();
  const matterId = params.matterId as string;
  const { data, isLoading } = usePortalMessages(matterId);
  const postMessage = usePostPortalMessage(matterId);
  const acknowledgeNotice = useAcknowledgeNotice(matterId);

  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [showCompose, setShowCompose] = useState(false);

  const handleSend = async () => {
    if (!body.trim()) return;
    await postMessage.mutateAsync({
      subject: subject.trim() || undefined,
      body: body.trim(),
    });
    setSubject("");
    setBody("");
    setShowCompose(false);
  };

  const handleAcknowledge = (commId: string) => {
    acknowledgeNotice.mutate(commId);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      </div>
    );
  }

  const messages = data?.messages ?? [];

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-serif font-medium text-foreground">
            Messages
          </h1>
          <p className="mt-2 text-muted-foreground">
            Communications about this estate.
          </p>
        </div>
        <Button
          onClick={() => setShowCompose(!showCompose)}
          className="gap-2 self-start"
        >
          <Send className="size-4" />
          Send a Message
        </Button>
      </div>

      {/* Compose form */}
      {showCompose && (
        <Card className="border-primary/20 shadow-sm">
          <CardContent className="p-6 space-y-4">
            <h3 className="text-sm font-medium text-foreground">New Message</h3>
            <p className="text-xs text-muted-foreground">
              Your message will be sent to the estate professionals managing this matter.
            </p>
            <Input
              placeholder="Subject (optional)"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="text-sm"
            />
            <Textarea
              placeholder="Type your message here..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={4}
              className="text-sm resize-none"
            />
            <div className="flex items-center gap-2 justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowCompose(false);
                  setSubject("");
                  setBody("");
                }}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSend}
                disabled={!body.trim() || postMessage.isPending}
                className="gap-1.5"
              >
                <Send className="size-3.5" />
                {postMessage.isPending ? "Sending..." : "Send"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Messages list */}
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="rounded-full bg-muted/50 p-5 mb-5">
            <MessageSquare className="size-8 text-muted-foreground/50" />
          </div>
          <h3 className="text-lg font-medium text-foreground mb-1">
            No messages yet
          </h3>
          <p className="text-sm text-muted-foreground max-w-md">
            Messages and notifications about this estate will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {messages.map((msg) => {
            const typeConfig = TYPE_CONFIG[msg.type] || TYPE_CONFIG.message;
            const TypeIcon = typeConfig.icon;

            return (
              <Card
                key={msg.id}
                className={cn(
                  "border-border/40 shadow-sm transition-shadow hover:shadow-md",
                  msg.requires_acknowledgment && !msg.acknowledged && "border-amber-200",
                )}
              >
                <CardContent className="p-6">
                  {/* Header */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          "flex size-9 items-center justify-center rounded-full",
                          msg.type === "distribution_notice"
                            ? "bg-amber-50"
                            : msg.type === "milestone_notification"
                              ? "bg-emerald-50"
                              : "bg-blue-50",
                        )}
                      >
                        <TypeIcon
                          className={cn(
                            "size-4",
                            msg.type === "distribution_notice"
                              ? "text-amber-600"
                              : msg.type === "milestone_notification"
                                ? "text-emerald-600"
                                : "text-blue-600",
                          )}
                        />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-foreground">
                            {msg.sender_name}
                          </p>
                          <Badge
                            variant="outline"
                            className={cn("text-[10px] px-1.5 py-0", typeConfig.color)}
                          >
                            {typeConfig.label}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(msg.created_at)}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Subject */}
                  {msg.subject && (
                    <h3 className="text-sm font-medium text-foreground mb-2">
                      {msg.subject}
                    </h3>
                  )}

                  {/* Body */}
                  <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">
                    {msg.body}
                  </p>

                  {/* Acknowledgment */}
                  {msg.requires_acknowledgment && (
                    <div className="mt-4 pt-4 border-t border-border/30">
                      {msg.acknowledged ? (
                        <div className="flex items-center gap-2 text-emerald-600">
                          <CheckCircle2 className="size-4" />
                          <span className="text-sm font-medium">Acknowledged</span>
                        </div>
                      ) : (
                        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                          <div className="flex items-center gap-2 text-amber-600">
                            <AlertCircle className="size-4" />
                            <span className="text-sm">
                              This notice requires your acknowledgment
                            </span>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-amber-200 text-amber-700 hover:bg-amber-50 gap-1.5"
                            onClick={() => handleAcknowledge(msg.id)}
                            disabled={acknowledgeNotice.isPending}
                          >
                            <CheckCircle2 className="size-3.5" />
                            Acknowledge
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
