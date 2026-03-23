"use client";

import { useState, useCallback } from "react";
import { Loader2, Download, CheckCircle2 } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DOC_TYPE_LABELS } from "@/lib/constants";
import { useRequestDocument, useApi } from "@/hooks";
import type { Stakeholder, Task, DocumentResponse } from "@/lib/types";

// ─── Document Request Dialog ──────────────────────────────────────────────────

interface DocumentRequestDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
  matterId: string;
  stakeholders: Stakeholder[];
  tasks: Task[];
}

export function DocumentRequestDialog({
  open,
  onOpenChange,
  firmId,
  matterId,
  stakeholders,
  tasks,
}: DocumentRequestDialogProps) {
  const requestDocument = useRequestDocument(firmId, matterId);
  const [stakeholderId, setStakeholderId] = useState("");
  const [docType, setDocType] = useState("");
  const [taskId, setTaskId] = useState("");
  const [message, setMessage] = useState("");

  const handleClose = useCallback(() => {
    setStakeholderId("");
    setDocType("");
    setTaskId("");
    setMessage("");
    onOpenChange(false);
  }, [onOpenChange]);

  const handleSubmit = async () => {
    if (!stakeholderId || !docType) return;

    try {
      await requestDocument.mutateAsync({
        target_stakeholder_id: stakeholderId,
        doc_type_needed: docType,
        task_id: taskId || null,
        message: message || undefined,
      });
      handleClose();
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Request Document</DialogTitle>
          <DialogDescription>
            Send a document request to a stakeholder via email.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Stakeholder */}
          <div>
            <Label>
              Request from <span className="text-danger">*</span>
            </Label>
            <Select value={stakeholderId} onValueChange={setStakeholderId}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Select stakeholder..." />
              </SelectTrigger>
              <SelectContent>
                {stakeholders.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.full_name} ({s.email})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Document type */}
          <div>
            <Label>
              Document type needed <span className="text-danger">*</span>
            </Label>
            <Select value={docType} onValueChange={setDocType}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Select type..." />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Link to task */}
          {tasks.length > 0 && (
            <div>
              <Label>Link to task (optional)</Label>
              <Select value={taskId || "__none__"} onValueChange={(v) => setTaskId(v === "__none__" ? "" : v)}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">None</SelectItem>
                  {tasks.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Message */}
          <div>
            <Label htmlFor="req-message">Custom message</Label>
            <Textarea
              id="req-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Optional instructions for the stakeholder..."
              rows={3}
              className="mt-1"
            />
          </div>

          {requestDocument.error && (
            <p className="text-sm text-danger">Failed to send request.</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={handleClose}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            disabled={!stakeholderId || !docType || requestDocument.isPending}
          >
            {requestDocument.isPending && <Loader2 className="size-4 mr-1 animate-spin" />}
            Send Request
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Bulk Download Dialog ─────────────────────────────────────────────────────

interface BulkDownloadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
  matterId: string;
  documents: DocumentResponse[];
}

export function BulkDownloadDialog({
  open,
  onOpenChange,
  firmId,
  matterId,
  documents,
}: BulkDownloadDialogProps) {
  const api = useApi();
  const [filterType, setFilterType] = useState<string>("all");
  const [status, setStatus] = useState<"idle" | "generating" | "ready" | "error">("idle");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const filteredDocs = filterType === "all"
    ? documents
    : documents.filter((d) => d.doc_type === filterType);

  const handleGenerate = async () => {
    setStatus("generating");
    try {
      const result = await api.bulkDownload(firmId, matterId, {
        document_ids: filteredDocs.map((d) => d.id),
      });
      // Poll for completion
      const pollInterval = setInterval(async () => {
        try {
          const statusResult = await api.getBulkDownloadStatus(
            firmId,
            matterId,
            result.job_id,
          );
          if (statusResult.status === "completed" && statusResult.download_url) {
            clearInterval(pollInterval);
            setDownloadUrl(statusResult.download_url);
            setStatus("ready");
          } else if (statusResult.status === "failed") {
            clearInterval(pollInterval);
            setStatus("error");
          }
        } catch {
          clearInterval(pollInterval);
          setStatus("error");
        }
      }, 2000);

      // Timeout after 60s
      setTimeout(() => {
        clearInterval(pollInterval);
        setStatus((curr) => (curr === "generating" ? "error" : curr));
      }, 60000);
    } catch {
      setStatus("error");
    }
  };

  const handleClose = () => {
    setStatus("idle");
    setDownloadUrl(null);
    setFilterType("all");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Bulk Download</DialogTitle>
          <DialogDescription>
            Generate a ZIP archive of documents.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {status === "idle" && (
            <>
              <div>
                <Label>Filter by type</Label>
                <Select value={filterType} onValueChange={setFilterType}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All documents ({documents.length})</SelectItem>
                    {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => {
                      const count = documents.filter((d) => d.doc_type === k).length;
                      if (count === 0) return null;
                      return (
                        <SelectItem key={k} value={k}>
                          {v} ({count})
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
              </div>
              <p className="text-sm text-muted-foreground">
                {filteredDocs.length} document{filteredDocs.length !== 1 ? "s" : ""} will be included.
              </p>
            </>
          )}

          {status === "generating" && (
            <div className="flex flex-col items-center py-6">
              <Loader2 className="size-8 text-primary animate-spin mb-3" />
              <p className="text-sm text-foreground">Generating ZIP archive...</p>
              <p className="text-xs text-muted-foreground mt-1">This may take a moment.</p>
            </div>
          )}

          {status === "ready" && downloadUrl && (
            <div className="flex flex-col items-center py-6">
              <CheckCircle2 className="size-8 text-success mb-3" />
              <p className="text-sm text-foreground mb-3">Download ready!</p>
              <Button onClick={() => window.open(downloadUrl, "_blank")}>
                <Download className="size-4 mr-1" />
                Download ZIP
              </Button>
            </div>
          )}

          {status === "error" && (
            <div className="flex flex-col items-center py-6">
              <p className="text-sm text-danger mb-2">Failed to generate download.</p>
              <Button variant="outline" size="sm" onClick={() => setStatus("idle")}>
                Try Again
              </Button>
            </div>
          )}
        </div>

        <DialogFooter>
          {status === "idle" && (
            <>
              <Button variant="ghost" onClick={handleClose}>Cancel</Button>
              <Button onClick={handleGenerate} disabled={filteredDocs.length === 0}>
                Generate Download
              </Button>
            </>
          )}
          {(status === "ready" || status === "error") && (
            <Button variant="ghost" onClick={handleClose}>Close</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
