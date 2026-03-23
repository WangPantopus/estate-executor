"use client";

import { useState } from "react";
import {
  X,
  Download,
  Sparkles,
  Check,
  FileText,
  Image,
  Link2,
  History,
  Loader2,
  Plus,
  Wand2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DOC_TYPE_LABELS } from "@/lib/constants";
import { useDocument, useConfirmDocType, useExtractData, useApi } from "@/hooks";
import { useToast } from "@/components/layout/Toaster";
import type { DocumentResponse, DocumentDetail } from "@/lib/types";
import type { AssetPrefillData } from "../../assets/_components/AddAssetDialog";
import { cn } from "@/lib/utils";

/** Doc types that support AI data extraction */
const EXTRACTABLE_TYPES = new Set([
  "account_statement",
  "deed",
  "insurance_policy",
  "trust_document",
  "appraisal",
  "tax_return",
]);

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function isPreviewable(mimeType: string): boolean {
  return (
    mimeType === "application/pdf" ||
    mimeType.startsWith("image/")
  );
}

// ─── Panel ────────────────────────────────────────────────────────────────────

interface DocumentDetailPanelProps {
  docId: string;
  firmId: string;
  matterId: string;
  documents: DocumentResponse[];
  onClose: () => void;
  /** Callback to open the Add Asset dialog with prefill data */
  onCreateAssetFromDoc?: (prefill: AssetPrefillData) => void;
}

export function DocumentDetailPanel({
  docId,
  firmId,
  matterId,
  documents,
  onClose,
  onCreateAssetFromDoc,
}: DocumentDetailPanelProps) {
  const api = useApi();
  const { toast } = useToast();
  const { data: docDetail, isLoading } = useDocument(firmId, matterId, docId);
  const confirmDocType = useConfirmDocType(firmId, matterId);
  const extractData = useExtractData(firmId, matterId);
  const [changingType, setChangingType] = useState(false);
  const [selectedType, setSelectedType] = useState<string>("");
  const [downloading, setDownloading] = useState(false);

  const doc: DocumentResponse | DocumentDetail | undefined =
    docDetail ?? documents.find((d) => d.id === docId);

  if (isLoading && !doc) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="h-5 w-40 bg-surface-elevated rounded animate-pulse" />
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>
        <div className="p-4 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-surface-elevated rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Document not found.</p>
      </div>
    );
  }

  const detail = docDetail as DocumentDetail | undefined;

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const { download_url } = await api.getDownloadUrl(firmId, matterId, doc.id);
      window.open(download_url, "_blank");
    } catch {
      // ignore
    }
    setDownloading(false);
  };

  const handleConfirmType = (docType: string) => {
    const wasCorrection = doc.doc_type !== null && doc.doc_type !== docType;
    confirmDocType.mutate(
      { docId: doc.id, data: { doc_type: docType } },
      {
        onSuccess: () => {
          setChangingType(false);
          if (wasCorrection) {
            toast("info", "AI learned from your correction — thank you for the feedback!");
          } else {
            toast("success", "Document type confirmed.");
          }
        },
      },
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border gap-2">
        <div className="min-w-0">
          <p className="text-lg font-medium text-foreground truncate">{doc.filename}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-muted-foreground">
              {formatFileSize(doc.size_bytes)}
            </span>
            <span className="text-xs text-muted-foreground">
              {formatDate(doc.created_at)}
            </span>
            {doc.current_version > 1 && (
              <Badge variant="outline" className="text-[10px]">v{doc.current_version}</Badge>
            )}
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
          <X className="size-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-5">
          {/* Preview */}
          {isPreviewable(doc.mime_type) && (
            <div className="rounded-lg border border-border overflow-hidden bg-surface-elevated">
              {doc.mime_type.startsWith("image/") ? (
                <div className="flex items-center justify-center p-4 min-h-[200px]">
                  <Image className="size-16 text-muted-foreground/30" />
                  <p className="text-xs text-muted-foreground ml-2">
                    Image preview (download to view)
                  </p>
                </div>
              ) : (
                <div className="flex items-center justify-center p-4 min-h-[200px]">
                  <FileText className="size-16 text-muted-foreground/30" />
                  <p className="text-xs text-muted-foreground ml-2">
                    PDF preview (download to view)
                  </p>
                </div>
              )}
            </div>
          )}

          <Separator />

          {/* AI Classification */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <Sparkles className="size-3.5 inline mr-1" />
              AI Classification
            </h3>
            {doc.doc_type ? (
              <div className="rounded-md border border-border p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">
                      {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
                    </span>
                    {doc.doc_type_confirmed ? (
                      <Badge variant="success" className="text-[10px]">
                        <Check className="size-2.5 mr-0.5" />
                        Confirmed
                      </Badge>
                    ) : (
                      <Badge variant="info" className="text-[10px]">AI Suggested</Badge>
                    )}
                  </div>
                  {doc.doc_type_confidence !== null && (
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {Math.round(doc.doc_type_confidence * 100)}% confidence
                    </span>
                  )}
                </div>

                {/* Confidence bar */}
                {doc.doc_type_confidence !== null && (
                  <div className="w-full h-1.5 bg-surface-elevated rounded-full mb-3">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        doc.doc_type_confidence >= 0.7
                          ? "bg-success"
                          : doc.doc_type_confidence >= 0.4
                            ? "bg-warning"
                            : "bg-danger",
                      )}
                      style={{ width: `${doc.doc_type_confidence * 100}%` }}
                    />
                  </div>
                )}

                {!doc.doc_type_confirmed && (
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleConfirmType(doc.doc_type!)}
                      disabled={confirmDocType.isPending}
                    >
                      {confirmDocType.isPending ? (
                        <Loader2 className="size-3.5 mr-1 animate-spin" />
                      ) : (
                        <Check className="size-3.5 mr-1" />
                      )}
                      Confirm
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedType(doc.doc_type ?? "");
                        setChangingType(true);
                      }}
                    >
                      Change Type
                    </Button>
                  </div>
                )}

                {changingType && (
                  <div className="flex items-center gap-2 mt-2">
                    <Select
                      value={selectedType}
                      onValueChange={setSelectedType}
                    >
                      <SelectTrigger className="h-8 flex-1">
                        <SelectValue placeholder="Select type..." />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      className="h-8"
                      onClick={() => handleConfirmType(selectedType)}
                      disabled={!selectedType || confirmDocType.isPending}
                    >
                      Save
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8"
                      onClick={() => setChangingType(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Not yet classified. AI classification may still be processing.
                </p>
                {/* Manual classification fallback */}
                <div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedType("");
                      setChangingType(true);
                    }}
                  >
                    Classify Manually
                  </Button>
                  {changingType && (
                    <div className="flex items-center gap-2 mt-2">
                      <Select value={selectedType} onValueChange={setSelectedType}>
                        <SelectTrigger className="h-8 flex-1">
                          <SelectValue placeholder="Select type..." />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => (
                            <SelectItem key={k} value={k}>{v}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        size="sm"
                        className="h-8"
                        onClick={() => handleConfirmType(selectedType)}
                        disabled={!selectedType || confirmDocType.isPending}
                      >
                        Save
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8"
                        onClick={() => setChangingType(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* AI Extracted Data */}
          {doc.ai_extracted_data && Object.keys(doc.ai_extracted_data).length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">
                  <Sparkles className="size-3.5 inline mr-1" />
                  AI Extracted Data
                </h3>
                <div className="rounded-md border border-info/30 bg-info-light/30 p-3 space-y-2">
                  {Object.entries(doc.ai_extracted_data)
                    .filter(([k, v]) => v !== null && v !== undefined && v !== "" && !k.startsWith("_"))
                    .map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground text-xs capitalize">
                          {key.replace(/_/g, " ")}
                        </span>
                        <span className="text-foreground font-medium">
                          {typeof value === "boolean"
                            ? value ? "Yes" : "No"
                            : Array.isArray(value)
                              ? value.join(", ")
                              : String(value)}
                        </span>
                      </div>
                    ))}
                </div>
                {onCreateAssetFromDoc && doc.doc_type && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-2 w-full"
                    onClick={() => {
                      const extracted = { ...doc.ai_extracted_data };
                      // Remove internal metadata before prefilling
                      delete extracted._extraction_metadata;
                      delete extracted.extraction_status;
                      delete extracted.classification_status;
                      onCreateAssetFromDoc({
                        docType: doc.doc_type!,
                        extractedData: extracted as Record<string, unknown>,
                        documentId: doc.id,
                      });
                    }}
                  >
                    <Plus className="size-3.5 mr-1" />
                    Create Asset from This
                  </Button>
                )}
              </div>
            </>
          )}

          {/* Extract Data button — shown when classified but not yet extracted */}
          {doc.doc_type &&
            EXTRACTABLE_TYPES.has(doc.doc_type) &&
            (!doc.ai_extracted_data ||
              Object.keys(doc.ai_extracted_data).filter(k => !k.startsWith("_") && k !== "classification_status" && k !== "extraction_status").length === 0) && (
            <>
              <Separator />
              <div>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  disabled={extractData.isPending}
                  onClick={() => extractData.mutate(doc.id)}
                >
                  {extractData.isPending ? (
                    <Loader2 className="size-3.5 mr-1 animate-spin" />
                  ) : (
                    <Wand2 className="size-3.5 mr-1" />
                  )}
                  Extract Data with AI
                </Button>
                {extractData.error && (
                  <p className="text-[10px] text-warning mt-1">
                    AI extraction unavailable. You can enter data manually on the asset.
                  </p>
                )}
              </div>
            </>
          )}

          <Separator />

          {/* Linked items */}
          {detail && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-2">
                <Link2 className="size-3.5 inline mr-1" />
                Linked Items
              </h3>
              {detail.linked_tasks.length > 0 && (
                <div className="mb-2">
                  <p className="text-xs text-muted-foreground mb-1">Tasks:</p>
                  <div className="space-y-1">
                    {detail.linked_tasks.map((task) => (
                      <div key={task.id} className="text-sm text-foreground bg-surface-elevated rounded-md px-3 py-1.5">
                        {task.title}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {detail.linked_assets.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Assets:</p>
                  <div className="space-y-1">
                    {detail.linked_assets.map((asset) => (
                      <div key={asset.id} className="text-sm text-foreground bg-surface-elevated rounded-md px-3 py-1.5">
                        {asset.title}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {detail.linked_tasks.length === 0 && detail.linked_assets.length === 0 && (
                <p className="text-sm text-muted-foreground">Not linked to any tasks or assets.</p>
              )}
            </div>
          )}

          {/* Versions */}
          {detail?.versions && detail.versions.length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">
                  <History className="size-3.5 inline mr-1" />
                  Version History
                </h3>
                <div className="space-y-1.5">
                  {detail.versions.map((ver) => (
                    <div
                      key={ver.id}
                      className="flex items-center justify-between text-sm rounded-md bg-surface-elevated px-3 py-2"
                    >
                      <div>
                        <span className="font-medium">v{ver.version_number}</span>
                        <span className="text-muted-foreground ml-2 text-xs">
                          {formatDateTime(ver.created_at)}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {formatFileSize(ver.size_bytes)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </ScrollArea>

      {/* Download footer */}
      <div className="border-t border-border p-4">
        <Button onClick={handleDownload} disabled={downloading} className="w-full">
          {downloading ? (
            <Loader2 className="size-4 mr-1 animate-spin" />
          ) : (
            <Download className="size-4 mr-1" />
          )}
          Download
        </Button>
      </div>
    </div>
  );
}
