"use client";

import { useState, useCallback, useRef } from "react";
import { Loader2, Send, Bold, Italic, List as ListIcon, Link2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateCommunication } from "@/hooks";
import type { Stakeholder, CommunicationType, CommunicationVisibility, CommunicationCreate } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

const COMPOSE_TYPES: { value: CommunicationType; label: string; description: string }[] = [
  { value: "message", label: "General Message", description: "Send a message to stakeholders" },
  { value: "milestone_notification", label: "Milestone Update", description: "Notify about an estate milestone" },
  { value: "distribution_notice", label: "Distribution Notice", description: "Formal notice requiring acknowledgment" },
];

const VISIBILITY_OPTIONS: { value: CommunicationVisibility; label: string }[] = [
  { value: "all_stakeholders", label: "All stakeholders" },
  { value: "professionals_only", label: "Professionals only" },
  { value: "specific", label: "Specific people" },
];

// ─── Component ────────────────────────────────────────────────────────────────

interface ComposeMessageProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
  matterId: string;
  stakeholders: Stakeholder[];
}

export function ComposeMessage({
  open,
  onOpenChange,
  firmId,
  matterId,
  stakeholders,
}: ComposeMessageProps) {
  const createComm = useCreateCommunication(firmId, matterId);

  const [type, setType] = useState<CommunicationType>("message");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [visibility, setVisibility] = useState<CommunicationVisibility>("all_stakeholders");
  const [visibleTo, setVisibleTo] = useState<string[]>([]);

  const isDistNotice = type === "distribution_notice";
  const subjectRequired = isDistNotice || type === "milestone_notification";

  const handleClose = useCallback(() => {
    setType("message");
    setSubject("");
    setBody("");
    setVisibility("all_stakeholders");
    setVisibleTo([]);
    onOpenChange(false);
  }, [onOpenChange]);

  const toggleRecipient = (stakeholderId: string) => {
    setVisibleTo((prev) =>
      prev.includes(stakeholderId)
        ? prev.filter((id) => id !== stakeholderId)
        : [...prev, stakeholderId],
    );
  };

  const canSend =
    body.trim().length > 0 &&
    (!subjectRequired || subject.trim().length > 0) &&
    (visibility !== "specific" || visibleTo.length > 0);

  const handleSend = async () => {
    if (!canSend) return;

    const payload: CommunicationCreate = {
      type,
      subject: subject.trim() || undefined,
      body: body.trim(),
      visibility,
      visible_to: visibility === "specific" ? visibleTo : undefined,
    };

    try {
      await createComm.mutateAsync(payload);
      handleClose();
    } catch {
      // Error handled by mutation
    }
  };

  const bodyRef = useRef<HTMLTextAreaElement>(null);

  const insertFormatting = (prefix: string, suffix: string) => {
    const el = bodyRef.current;
    if (!el) {
      setBody((prev) => prev + prefix + suffix);
      return;
    }
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const selected = body.substring(start, end);
    const newText = body.substring(0, start) + prefix + selected + suffix + body.substring(end);
    setBody(newText);
    // Restore cursor after prefix + selected text
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + prefix.length, start + prefix.length + selected.length);
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>New Message</DialogTitle>
          <DialogDescription>
            Compose a message to matter stakeholders.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Message type */}
          <div>
            <Label>Message Type</Label>
            <div className="grid grid-cols-3 gap-2 mt-1.5">
              {COMPOSE_TYPES.map((ct) => (
                <button
                  key={ct.value}
                  type="button"
                  onClick={() => setType(ct.value)}
                  className={cn(
                    "rounded-lg border p-2.5 text-left transition-all",
                    type === ct.value
                      ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                      : "border-border hover:border-primary/30",
                  )}
                >
                  <p className="text-xs font-medium text-foreground">{ct.label}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{ct.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Subject */}
          <div>
            <Label htmlFor="compose-subject">
              Subject {subjectRequired && <span className="text-danger">*</span>}
            </Label>
            <Input
              id="compose-subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder={
                isDistNotice
                  ? "e.g. Distribution of Estate Assets — Phase 1"
                  : "Optional subject line"
              }
              className="mt-1"
            />
          </div>

          {/* Body with mini toolbar */}
          <div>
            <Label htmlFor="compose-body">
              Message <span className="text-danger">*</span>
            </Label>
            <div className="mt-1 rounded-md border border-border overflow-hidden focus-within:ring-2 focus-within:ring-ring/40">
              {/* Mini formatting toolbar */}
              <div className="flex items-center gap-0.5 px-2 py-1 border-b border-border bg-surface-elevated/50">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  onClick={() => insertFormatting("**", "**")}
                  title="Bold"
                >
                  <Bold className="size-3.5" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  onClick={() => insertFormatting("_", "_")}
                  title="Italic"
                >
                  <Italic className="size-3.5" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  onClick={() => insertFormatting("\n- ", "")}
                  title="List"
                >
                  <ListIcon className="size-3.5" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  onClick={() => insertFormatting("[", "](url)")}
                  title="Link"
                >
                  <Link2 className="size-3.5" />
                </Button>
              </div>
              <Textarea
                ref={bodyRef}
                id="compose-body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Type your message..."
                rows={6}
                className="border-0 rounded-none focus-visible:ring-0"
              />
            </div>
          </div>

          {/* Visibility */}
          <div>
            <Label>Visibility</Label>
            <Select
              value={visibility}
              onValueChange={(v) => setVisibility(v as CommunicationVisibility)}
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VISIBILITY_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {visibility === "professionals_only" && (
              <p className="text-xs text-muted-foreground mt-1">
                Only matter admins and professionals will see this message.
              </p>
            )}
          </div>

          {/* Specific recipients */}
          {visibility === "specific" && (
            <div>
              <Label>Recipients <span className="text-danger">*</span></Label>
              <div className="max-h-40 overflow-y-auto rounded-md border border-border p-2 mt-1 space-y-1">
                {stakeholders.map((s) => (
                  <label
                    key={s.id}
                    className="flex items-center gap-2 text-sm cursor-pointer hover:bg-surface-elevated rounded px-2 py-1.5"
                  >
                    <input
                      type="checkbox"
                      checked={visibleTo.includes(s.id)}
                      onChange={() => toggleRecipient(s.id)}
                      className="size-3.5 rounded border-border text-primary focus:ring-primary/40"
                    />
                    <span className="text-foreground">{s.full_name}</span>
                    <span className="text-xs text-muted-foreground ml-auto capitalize">
                      {s.role.replace(/_/g, " ")}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Distribution notice note */}
          {isDistNotice && (
            <div className="rounded-md bg-info-light/30 border border-info/20 p-3">
              <p className="text-xs text-info">
                Distribution notices require recipients to acknowledge receipt. All beneficiaries and executors will be prompted to acknowledge.
              </p>
            </div>
          )}

          {/* Error */}
          {createComm.error && (
            <p className="text-sm text-danger">Failed to send message.</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={handleClose}>Cancel</Button>
          <Button
            onClick={handleSend}
            disabled={!canSend || createComm.isPending}
          >
            {createComm.isPending ? (
              <Loader2 className="size-4 mr-1 animate-spin" />
            ) : (
              <Send className="size-4 mr-1" />
            )}
            Send
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
