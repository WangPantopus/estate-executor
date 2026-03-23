"use client";

import {
  FileText,
  Image,
  FileSpreadsheet,
  File,
  Sparkles,
  Check,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { DOC_TYPE_LABELS } from "@/lib/constants";
import type { DocumentResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith("image/")) return <Image alt="" className="size-5" />;
  if (mimeType === "application/pdf") return <FileText className="size-5" />;
  if (
    mimeType.includes("spreadsheet") ||
    mimeType.includes("excel") ||
    mimeType === "text/csv"
  )
    return <FileSpreadsheet className="size-5" />;
  if (mimeType.includes("word") || mimeType.includes("document"))
    return <FileText className="size-5" />;
  return <File className="size-5" />;
}

function getFileIconColor(mimeType: string): string {
  if (mimeType.startsWith("image/")) return "text-emerald-600 bg-emerald-50";
  if (mimeType === "application/pdf") return "text-red-600 bg-red-50";
  if (mimeType.includes("spreadsheet") || mimeType.includes("excel"))
    return "text-green-600 bg-green-50";
  if (mimeType.includes("word")) return "text-blue-600 bg-blue-50";
  return "text-gray-500 bg-gray-100";
}

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

function DocTypeBadge({ doc }: { doc: DocumentResponse }) {
  if (!doc.doc_type) return <Badge variant="muted" className="text-[10px]">Unclassified</Badge>;

  if (doc.doc_type_confirmed) {
    return (
      <Badge variant="success" className="text-[10px]">
        <Check className="size-2.5 mr-0.5" />
        {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
      </Badge>
    );
  }

  return (
    <Badge variant="info" className="text-[10px]">
      <Sparkles className="size-2.5 mr-0.5" />
      {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
    </Badge>
  );
}

// ─── Card View ────────────────────────────────────────────────────────────────

interface DocumentCardProps {
  doc: DocumentResponse;
  onClick: () => void;
}

export function DocumentCard({ doc, onClick }: DocumentCardProps) {
  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30 group"
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* File icon */}
          <div
            className={cn(
              "flex items-center justify-center size-10 rounded-lg shrink-0",
              getFileIconColor(doc.mime_type),
            )}
          >
            {getFileIcon(doc.mime_type)}
          </div>

          <div className="flex-1 min-w-0">
            {/* Filename */}
            <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
              {doc.filename}
            </p>

            {/* Type badge */}
            <div className="flex items-center gap-2 mt-1">
              <DocTypeBadge doc={doc} />
              {doc.current_version > 1 && (
                <Badge variant="outline" className="text-[10px]">
                  v{doc.current_version}
                </Badge>
              )}
            </div>

            {/* Meta row */}
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
              <span>{formatDate(doc.created_at)}</span>
              <span>{formatFileSize(doc.size_bytes)}</span>
            </div>

            {/* AI confidence indicator */}
            {doc.doc_type && !doc.doc_type_confirmed && doc.doc_type_confidence !== null && (
              <div className="mt-1.5">
                <div className="flex items-center gap-1.5">
                  <div className="flex-1 h-1 bg-surface-elevated rounded-full">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        doc.doc_type_confidence >= 0.7
                          ? "bg-success"
                          : doc.doc_type_confidence >= 0.4
                            ? "bg-warning"
                            : "bg-danger",
                      )}
                      style={{ width: `${doc.doc_type_confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-muted-foreground tabular-nums">
                    {Math.round(doc.doc_type_confidence * 100)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── List View ────────────────────────────────────────────────────────────────

interface DocumentListViewProps {
  documents: DocumentResponse[];
  onDocClick: (docId: string) => void;
}

export function DocumentListView({ documents, onDocClick }: DocumentListViewProps) {
  return (
    <div className="rounded-lg border border-border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Filename</TableHead>
            <TableHead>Type</TableHead>
            <TableHead className="hidden sm:table-cell">Uploaded</TableHead>
            <TableHead className="hidden md:table-cell">Size</TableHead>
            <TableHead className="hidden md:table-cell">Version</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow
              key={doc.id}
              className="cursor-pointer"
              onClick={() => onDocClick(doc.id)}
            >
              <TableCell>
                <div className="flex items-center gap-2">
                  <span className={cn("shrink-0", getFileIconColor(doc.mime_type).split(" ")[0])}>
                    {getFileIcon(doc.mime_type)}
                  </span>
                  <span className="font-medium truncate max-w-[200px]">{doc.filename}</span>
                </div>
              </TableCell>
              <TableCell>
                <DocTypeBadge doc={doc} />
              </TableCell>
              <TableCell className="hidden sm:table-cell text-muted-foreground">
                {formatDate(doc.created_at)}
              </TableCell>
              <TableCell className="hidden md:table-cell text-muted-foreground tabular-nums">
                {formatFileSize(doc.size_bytes)}
              </TableCell>
              <TableCell className="hidden md:table-cell text-muted-foreground">
                {doc.current_version > 1 ? `v${doc.current_version}` : "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
