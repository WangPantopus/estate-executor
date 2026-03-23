"use client";

import { useState } from "react";
import {
  Copy,
  Download,
  Loader2,
  Check,
  Sparkles,
  Mail,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useDraftLetter } from "@/hooks";
import type { AILetterDraftResponse } from "@/lib/types";

// ─── Letter type definitions ─────────────────────────────────────────────────

const LETTER_TYPES: Record<string, { label: string; description: string }> = {
  institution_notification: {
    label: "Institution Death Notification",
    description: "Notify bank, brokerage, or insurance company of death",
  },
  creditor_notification: {
    label: "Creditor Notification",
    description: "Formal notice to a creditor regarding the estate",
  },
  beneficiary_notification: {
    label: "Beneficiary Notification",
    description: "Notify a beneficiary of their interest in the estate",
  },
  government_agency: {
    label: "Government Agency Notification",
    description: "Notify SSA, DMV, IRS, or other agency of death",
  },
  subscription_cancellation: {
    label: "Subscription Cancellation",
    description: "Cancel a recurring subscription or service",
  },
  insurance_claim: {
    label: "Insurance Claim Initiation",
    description: "Initiate a life insurance death benefit claim",
  },
};

// ─── Dialog ──────────────────────────────────────────────────────────────────

interface DraftLetterDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
  matterId: string;
  assetId: string;
  assetTitle: string;
  institution?: string | null;
}

export function DraftLetterDialog({
  open,
  onOpenChange,
  firmId,
  matterId,
  assetId,
  assetTitle,
  institution,
}: DraftLetterDialogProps) {
  const draftLetter = useDraftLetter(firmId, matterId);
  const [letterType, setLetterType] = useState<string>("");
  const [draft, setDraft] = useState<AILetterDraftResponse | null>(null);
  const [editedBody, setEditedBody] = useState("");
  const [editedSubject, setEditedSubject] = useState("");
  const [copied, setCopied] = useState(false);

  const handleGenerate = () => {
    if (!letterType) return;

    draftLetter.mutate(
      { asset_id: assetId, letter_type: letterType },
      {
        onSuccess: (result) => {
          setDraft(result);
          setEditedBody(result.body);
          setEditedSubject(result.subject);
        },
      },
    );
  };

  const handleCopy = async () => {
    const text = `Subject: ${editedSubject}\n\n${editedBody}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadPdf = () => {
    // Escape HTML entities to prevent XSS in the print window
    const escapeHtml = (str: string) =>
      str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");

    const safeSubject = escapeHtml(editedSubject);
    const safeBody = escapeHtml(editedBody).replace(/\n/g, "<br>");

    const html = `<!DOCTYPE html>
<html><head>
<style>
  body { font-family: 'Times New Roman', serif; max-width: 700px; margin: 40px auto; padding: 40px; line-height: 1.6; }
  h1 { font-size: 14px; font-weight: bold; margin-bottom: 20px; }
  p { margin-bottom: 12px; }
  .body-text { white-space: pre-wrap; }
</style>
</head><body>
<h1>${safeSubject}</h1>
<div class="body-text">${safeBody}</div>
</body></html>`;

    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const printWindow = window.open(url, "_blank");
    if (printWindow) {
      printWindow.addEventListener("load", () => {
        printWindow.print();
      });
    }
  };

  const handleClose = () => {
    setDraft(null);
    setLetterType("");
    setEditedBody("");
    setEditedSubject("");
    setCopied(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="size-5" />
            Draft Letter
          </DialogTitle>
          <DialogDescription>
            Generate an AI-drafted letter for {assetTitle}
            {institution ? ` at ${institution}` : ""}.
          </DialogDescription>
        </DialogHeader>

        {!draft ? (
          /* ── Step 1: Select letter type ── */
          <div className="space-y-4">
            <div>
              <Label>Letter Type</Label>
              <Select value={letterType} onValueChange={setLetterType}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select letter type..." />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(LETTER_TYPES).map(([key, { label, description }]) => (
                    <SelectItem key={key} value={key}>
                      <div>
                        <span className="font-medium">{label}</span>
                        <span className="text-xs text-muted-foreground ml-2">
                          — {description}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {letterType && (
              <div className="rounded-md border border-info/30 bg-info-light/30 px-3 py-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <Sparkles className="size-3.5 text-info" />
                  <span className="text-xs font-medium text-info">
                    {LETTER_TYPES[letterType].label}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {LETTER_TYPES[letterType].description}
                </p>
              </div>
            )}

            {draftLetter.error && (
              <p className="text-sm text-danger">
                Failed to generate letter. Please try again.
              </p>
            )}

            <DialogFooter>
              <Button variant="ghost" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={handleGenerate}
                disabled={!letterType || draftLetter.isPending}
              >
                {draftLetter.isPending ? (
                  <Loader2 className="size-4 mr-1 animate-spin" />
                ) : (
                  <Sparkles className="size-4 mr-1" />
                )}
                Generate Letter
              </Button>
            </DialogFooter>
          </div>
        ) : (
          /* ── Step 2: Review and edit ── */
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Badge variant="success" className="text-xs">
                <Check className="size-3 mr-0.5" />
                Generated
              </Badge>
              <span className="text-xs text-muted-foreground">
                To: {draft.recipient_institution}
              </span>
            </div>

            <div>
              <Label htmlFor="letter-subject">Subject</Label>
              <Input
                id="letter-subject"
                value={editedSubject}
                onChange={(e) => setEditedSubject(e.target.value)}
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="letter-body">Letter Body</Label>
              <Textarea
                id="letter-body"
                value={editedBody}
                onChange={(e) => setEditedBody(e.target.value)}
                rows={16}
                className="mt-1 font-serif text-sm leading-relaxed"
              />
            </div>

            <Separator />

            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button variant="ghost" onClick={handleClose} className="sm:mr-auto">
                Close
              </Button>
              <Button
                variant="outline"
                onClick={handleCopy}
              >
                {copied ? (
                  <Check className="size-4 mr-1" />
                ) : (
                  <Copy className="size-4 mr-1" />
                )}
                {copied ? "Copied!" : "Copy to Clipboard"}
              </Button>
              <Button
                variant="outline"
                onClick={handleDownloadPdf}
              >
                <Download className="size-4 mr-1" />
                Print / Save as PDF
              </Button>
              <Button
                onClick={() => {
                  draftLetter.mutate(
                    { asset_id: assetId, letter_type: letterType },
                    {
                      onSuccess: (result) => {
                        setDraft(result);
                        setEditedBody(result.body);
                        setEditedSubject(result.subject);
                      },
                    },
                  );
                }}
                disabled={draftLetter.isPending}
              >
                {draftLetter.isPending ? (
                  <Loader2 className="size-4 mr-1 animate-spin" />
                ) : (
                  <Sparkles className="size-4 mr-1" />
                )}
                Regenerate
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
