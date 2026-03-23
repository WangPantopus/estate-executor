"use client";

import { use } from "react";
import { FileText, Download, File, Image, FileSpreadsheet } from "lucide-react";
import { useDocuments } from "@/hooks";
import { useApi } from "@/hooks/use-api";
import { LoadingState } from "@/components/layout/LoadingState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/layout/Toaster";
import type { DocumentResponse } from "@/lib/types";

const FIRM_ID = "current";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith("image/")) return Image;
  if (mimeType.includes("spreadsheet") || mimeType.includes("excel"))
    return FileSpreadsheet;
  if (mimeType.includes("pdf")) return FileText;
  return File;
}

function getDocTypeLabel(docType: string | null): string {
  if (!docType) return "Document";
  return docType
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

interface DocumentRowProps {
  doc: DocumentResponse;
  firmId: string;
  matterId: string;
}

function DocumentRow({ doc, firmId, matterId }: DocumentRowProps) {
  const api = useApi();
  const { toast } = useToast();
  const Icon = getFileIcon(doc.mime_type);

  const handleDownload = async () => {
    try {
      const { download_url } = await api.getDownloadUrl(
        firmId,
        matterId,
        doc.id,
      );
      window.open(download_url, "_blank");
    } catch {
      toast("error", "Failed to download document. Please try again.");
    }
  };

  return (
    <div className="flex items-center gap-4 rounded-lg border border-border bg-card p-4 sm:p-5 hover:border-border/80 transition-colors">
      {/* File icon */}
      <div className="flex size-10 items-center justify-center rounded-lg bg-surface-elevated shrink-0">
        <Icon className="size-5 text-muted-foreground" />
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">
          {doc.filename}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-muted-foreground">
            {getDocTypeLabel(doc.doc_type)}
          </span>
          <span className="text-xs text-muted-foreground/50">·</span>
          <span className="text-xs text-muted-foreground">
            {formatFileSize(doc.size_bytes)}
          </span>
          <span className="text-xs text-muted-foreground/50">·</span>
          <span className="text-xs text-muted-foreground">
            {formatDate(doc.created_at)}
          </span>
        </div>
      </div>

      {/* Download button */}
      <Button
        variant="outline"
        size="sm"
        onClick={handleDownload}
        className="shrink-0"
      >
        <Download className="size-4 sm:mr-1.5" />
        <span className="hidden sm:inline">Download</span>
      </Button>
    </div>
  );
}

export default function PortalDocumentsPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);
  const { data: docsData, isLoading, error } = useDocuments(FIRM_ID, matterId);

  if (isLoading) {
    return <LoadingState variant="list" />;
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-danger">Unable to load documents.</p>
          <p className="text-sm text-muted-foreground mt-2">
            Please try refreshing the page.
          </p>
        </CardContent>
      </Card>
    );
  }

  const documents = docsData?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-serif font-semibold text-foreground">
          Documents
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Documents shared with you by the estate administrator.
        </p>
      </div>

      {/* Document list */}
      {documents.length === 0 ? (
        <div className="rounded-xl border border-border bg-card py-16 text-center">
          <FileText className="size-10 text-muted-foreground/30 mx-auto mb-4" />
          <p className="text-sm font-medium text-foreground">
            No documents shared yet
          </p>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
            Documents will appear here as your estate administrator shares
            them with you.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <DocumentRow
              key={doc.id}
              doc={doc}
              firmId={FIRM_ID}
              matterId={matterId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
