"use client";

import { useState, useCallback, useRef } from "react";
import { Upload, X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/hooks";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface UploadItem {
  id: string;
  file: File;
  status: "pending" | "uploading" | "registering" | "done" | "error";
  progress: number;
  error?: string;
}

interface DocumentUploadZoneProps {
  firmId: string;
  matterId: string;
  compact?: boolean;
  taskId?: string | null;
  assetId?: string | null;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DocumentUploadZone({
  firmId,
  matterId,
  compact = false,
  taskId,
  assetId,
}: DocumentUploadZoneProps) {
  const api = useApi();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploads, setUploads] = useState<UploadItem[]>([]);

  const updateUpload = useCallback(
    (id: string, patch: Partial<UploadItem>) => {
      setUploads((prev) =>
        prev.map((u) => (u.id === id ? { ...u, ...patch } : u)),
      );
    },
    [],
  );

  const processFile = useCallback(
    async (item: UploadItem) => {
      try {
        // Step 1: Get presigned URL
        updateUpload(item.id, { status: "uploading", progress: 10 });
        const { upload_url, storage_key } = await api.getUploadUrl(
          firmId,
          matterId,
          {
            filename: item.file.name,
            mime_type: item.file.type || "application/octet-stream",
          },
        );

        // Step 2: Upload to S3/MinIO
        updateUpload(item.id, { progress: 30 });
        const uploadResp = await fetch(upload_url, {
          method: "PUT",
          body: item.file,
          headers: { "Content-Type": item.file.type || "application/octet-stream" },
        });
        if (!uploadResp.ok) throw new Error("Upload failed");

        // Step 3: Register document
        updateUpload(item.id, { status: "registering", progress: 70 });
        await api.registerDocument(firmId, matterId, {
          filename: item.file.name,
          storage_key,
          mime_type: item.file.type || "application/octet-stream",
          size_bytes: item.file.size,
          task_id: taskId ?? null,
          asset_id: assetId ?? null,
        });

        updateUpload(item.id, { status: "done", progress: 100 });
        qc.invalidateQueries({ queryKey: queryKeys.documents(firmId, matterId) });
        qc.invalidateQueries({
          queryKey: queryKeys.matterDashboard(firmId, matterId),
        });
      } catch (err) {
        updateUpload(item.id, {
          status: "error",
          error: err instanceof Error ? err.message : "Upload failed",
        });
      }
    },
    [api, firmId, matterId, taskId, assetId, qc, updateUpload],
  );

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      const newItems: UploadItem[] = Array.from(files).map((file) => ({
        id: `${file.name}-${Date.now()}-${Math.random()}`,
        file,
        status: "pending" as const,
        progress: 0,
      }));

      setUploads((prev) => [...prev, ...newItems]);

      // Start uploading each file
      for (const item of newItems) {
        processFile(item);
      }
    },
    [processFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles],
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const removeUpload = (id: string) => {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  };

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "relative border-2 border-dashed rounded-lg transition-all cursor-pointer",
          "flex flex-col items-center justify-center text-center",
          compact ? "p-4" : "p-8",
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/40 hover:bg-surface-elevated/50",
        )}
      >
        <Upload
          className={cn(
            "text-muted-foreground mb-2",
            compact ? "size-5" : "size-8",
          )}
        />
        <p className={cn("font-medium text-foreground", compact ? "text-xs" : "text-sm")}>
          {dragOver ? "Drop files here" : "Drop files or click to upload"}
        </p>
        {!compact && (
          <p className="text-xs text-muted-foreground mt-1">
            PDF, Word, images, and other documents
          </p>
        )}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {/* Upload progress items */}
      {uploads.length > 0 && (
        <div className="space-y-2">
          {uploads.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-3 rounded-md border border-border bg-card px-3 py-2"
            >
              {item.status === "done" ? (
                <CheckCircle2 className="size-4 text-success shrink-0" />
              ) : item.status === "error" ? (
                <AlertCircle className="size-4 text-danger shrink-0" />
              ) : (
                <Loader2 className="size-4 text-primary animate-spin shrink-0" />
              )}

              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground truncate">
                  {item.file.name}
                </p>
                <div className="flex items-center gap-2">
                  {item.status === "uploading" && (
                    <p className="text-[10px] text-muted-foreground">Uploading...</p>
                  )}
                  {item.status === "registering" && (
                    <p className="text-[10px] text-info">Classifying...</p>
                  )}
                  {item.status === "done" && (
                    <p className="text-[10px] text-success">Uploaded</p>
                  )}
                  {item.status === "error" && (
                    <p className="text-[10px] text-danger">{item.error}</p>
                  )}
                </div>
                {/* Progress bar */}
                {(item.status === "uploading" || item.status === "registering") && (
                  <div className="w-full h-1 bg-surface-elevated rounded-full mt-1">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                )}
              </div>

              <Button
                variant="ghost"
                size="icon"
                className="size-6 shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  removeUpload(item.id);
                }}
              >
                <X className="size-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
