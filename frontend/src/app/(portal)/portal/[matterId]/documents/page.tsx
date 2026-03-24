"use client";

import { useParams } from "next/navigation";
import { usePortalDocuments } from "@/hooks/use-portal-queries";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Download } from "lucide-react";

const DOC_TYPE_LABELS: Record<string, string> = {
  death_certificate: "Death Certificate",
  court_filing: "Court Filing",
  distribution_notice: "Distribution Notice",
  correspondence: "Correspondence",
  will: "Will",
  trust_document: "Trust Document",
  appraisal: "Appraisal",
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default function PortalDocumentsPage() {
  const params = useParams();
  const matterId = params.matterId as string;
  const { data, isLoading } = usePortalDocuments(matterId);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      </div>
    );
  }

  const documents = data?.documents ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-serif font-medium text-foreground">
          Shared Documents
        </h1>
        <p className="mt-2 text-muted-foreground">
          Documents that have been shared with you regarding this estate.
        </p>
      </div>

      {documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="rounded-full bg-muted/50 p-5 mb-5">
            <FileText className="size-8 text-muted-foreground/50" />
          </div>
          <h3 className="text-lg font-medium text-foreground mb-1">
            No documents yet
          </h3>
          <p className="text-sm text-muted-foreground max-w-md">
            Documents will appear here as they are shared with you by the estate
            administrator.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <Card
              key={doc.id}
              className="border-border/40 shadow-sm hover:shadow-md transition-shadow"
            >
              <CardContent className="flex items-center gap-4 p-5">
                {/* Icon */}
                <div className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-primary/5">
                  <FileText className="size-6 text-primary/70" />
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {doc.filename}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    {doc.doc_type && (
                      <span className="text-xs text-muted-foreground">
                        {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {formatFileSize(doc.size_bytes)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Shared {formatDate(doc.shared_at)}
                    </span>
                  </div>
                </div>

                {/* Download button */}
                <Button
                  variant="outline"
                  size="sm"
                  className="shrink-0 gap-1.5"
                >
                  <Download className="size-3.5" />
                  <span className="hidden sm:inline">Download</span>
                </Button>
              </CardContent>
            </Card>
          ))}

          <p className="text-xs text-center text-muted-foreground pt-4">
            {documents.length} document{documents.length !== 1 ? "s" : ""} shared
          </p>
        </div>
      )}
    </div>
  );
}
