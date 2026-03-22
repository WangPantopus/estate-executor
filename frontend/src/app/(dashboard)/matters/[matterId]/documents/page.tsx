"use client";

import { use, useState, useMemo } from "react";
import {
  Upload,
  FileQuestion,
  Download,
  Filter,
  LayoutGrid,
  List,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
} from "@/components/ui/sheet";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import { EmptyState } from "@/components/layout/EmptyState";
import { useDocuments, useStakeholders, useTasks } from "@/hooks";
import type { DocumentResponse } from "@/lib/types";

import { DocumentUploadZone } from "./_components/DocumentUploadZone";
import { DocumentCard, DocumentListView } from "./_components/DocumentViews";
import {
  DocumentFilterBar,
  type DocFilterState,
  EMPTY_DOC_FILTERS,
  countActiveDocFilters,
} from "./_components/DocumentFilterBar";
import { DocumentDetailPanel } from "./_components/DocumentDetailPanel";
import {
  DocumentRequestDialog,
  BulkDownloadDialog,
} from "./_components/DocumentDialogs";

// ─── Constants ────────────────────────────────────────────────────────────────

const FIRM_ID = "current";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DocumentsPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);

  // ─── Data fetching ──────────────────────────────────────────────────────────
  const {
    data: docsData,
    isLoading,
    error,
  } = useDocuments(FIRM_ID, matterId);
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);
  const { data: tasksData } = useTasks(FIRM_ID, matterId, { per_page: 200 });

  const allDocs = docsData?.data ?? [];
  const stakeholders = stakeholdersData?.data ?? [];
  const tasks = tasksData?.data ?? [];

  // ─── UI state ───────────────────────────────────────────────────────────────
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<DocFilterState>(EMPTY_DOC_FILTERS);
  const [detailDocId, setDetailDocId] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [requestDialogOpen, setRequestDialogOpen] = useState(false);
  const [bulkDownloadOpen, setBulkDownloadOpen] = useState(false);

  // ─── Filter logic ───────────────────────────────────────────────────────────
  const filteredDocs = useMemo(() => {
    let result = allDocs;

    if (filters.docType) {
      result = result.filter((d) => d.doc_type === filters.docType);
    }

    if (filters.confirmationStatus !== "all") {
      switch (filters.confirmationStatus) {
        case "confirmed":
          result = result.filter((d) => d.doc_type_confirmed);
          break;
        case "ai_suggested":
          result = result.filter((d) => d.doc_type && !d.doc_type_confirmed);
          break;
        case "unclassified":
          result = result.filter((d) => !d.doc_type);
          break;
      }
    }

    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter((d) => d.filename.toLowerCase().includes(q));
    }

    return result;
  }, [allDocs, filters]);

  const activeFilterCount = countActiveDocFilters(filters);

  // ─── Render ─────────────────────────────────────────────────────────────────
  if (isLoading) {
    return <LoadingState variant="cards" />;
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-danger">Failed to load documents.</p>
        <p className="text-sm text-muted-foreground mt-1">
          Please try refreshing the page.
        </p>
      </div>
    );
  }

  const hasDocuments = allDocs.length > 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <PageHeader
        title="Documents"
        actions={
          <div className="flex items-center gap-2">
            {/* Filter toggle */}
            <Button
              variant={showFilters ? "outline" : "ghost"}
              size="sm"
              onClick={() => setShowFilters((v) => !v)}
            >
              <Filter className="size-4 mr-1" />
              Filters
              {activeFilterCount > 0 && (
                <Badge
                  variant="default"
                  className="ml-1.5 size-5 p-0 flex items-center justify-center text-[10px]"
                >
                  {activeFilterCount}
                </Badge>
              )}
            </Button>

            {/* View toggle */}
            {hasDocuments && (
              <div className="hidden sm:flex items-center rounded-md border border-border">
                <Button
                  variant={viewMode === "grid" ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("grid")}
                  className="rounded-r-none border-0"
                >
                  <LayoutGrid className="size-4" />
                </Button>
                <Button
                  variant={viewMode === "list" ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("list")}
                  className="rounded-l-none border-0"
                >
                  <List className="size-4" />
                </Button>
              </div>
            )}

            {/* Request document */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRequestDialogOpen(true)}
            >
              <FileQuestion className="size-4 mr-1" />
              <span className="hidden sm:inline">Request</span>
            </Button>

            {/* Bulk download */}
            {hasDocuments && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setBulkDownloadOpen(true)}
              >
                <Download className="size-4 mr-1" />
                <span className="hidden sm:inline">Bulk</span>
              </Button>
            )}

            {/* Upload */}
            <Button size="sm" onClick={() => setShowUpload((v) => !v)}>
              <Upload className="size-4 mr-1" />
              Upload
            </Button>
          </div>
        }
      />

      {/* Upload zone */}
      {(showUpload || !hasDocuments) && (
        <DocumentUploadZone
          firmId={FIRM_ID}
          matterId={matterId}
          compact={hasDocuments}
        />
      )}

      {/* Filter panel */}
      {showFilters && (
        <DocumentFilterBar filters={filters} onChange={setFilters} />
      )}

      {/* Document count */}
      {hasDocuments && (
        <p className="text-xs text-muted-foreground">
          {filteredDocs.length} document{filteredDocs.length !== 1 ? "s" : ""}
          {activeFilterCount > 0 && ` (filtered from ${allDocs.length})`}
        </p>
      )}

      {/* Content */}
      {filteredDocs.length === 0 && hasDocuments ? (
        <EmptyState
          title="No documents match filters"
          description="Try adjusting your filters to see more documents."
          action={
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setFilters(EMPTY_DOC_FILTERS);
                setShowFilters(false);
              }}
            >
              Clear filters
            </Button>
          }
        />
      ) : filteredDocs.length === 0 ? (
        <EmptyState
          title="No documents yet"
          description="Upload documents or request them from stakeholders."
        />
      ) : viewMode === "grid" ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredDocs.map((doc) => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              onClick={() => setDetailDocId(doc.id)}
            />
          ))}
        </div>
      ) : (
        <DocumentListView
          documents={filteredDocs}
          onDocClick={(id) => setDetailDocId(id)}
        />
      )}

      {/* Document detail side panel */}
      <Sheet
        open={!!detailDocId}
        onOpenChange={(open) => {
          if (!open) setDetailDocId(null);
        }}
      >
        <SheetContent side="right" className="w-full sm:max-w-lg p-0">
          {detailDocId && (
            <DocumentDetailPanel
              docId={detailDocId}
              firmId={FIRM_ID}
              matterId={matterId}
              documents={allDocs}
              onClose={() => setDetailDocId(null)}
            />
          )}
        </SheetContent>
      </Sheet>

      {/* Document request dialog */}
      <DocumentRequestDialog
        open={requestDialogOpen}
        onOpenChange={setRequestDialogOpen}
        firmId={FIRM_ID}
        matterId={matterId}
        stakeholders={stakeholders}
        tasks={tasks}
      />

      {/* Bulk download dialog */}
      <BulkDownloadDialog
        open={bulkDownloadOpen}
        onOpenChange={setBulkDownloadOpen}
        firmId={FIRM_ID}
        matterId={matterId}
        documents={allDocs}
      />
    </div>
  );
}
