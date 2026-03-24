"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface RequestInfo {
  request_id: string;
  matter_title: string;
  decedent_name: string;
  requester_name: string;
  doc_type_needed: string;
  message: string | null;
  status: string;
  expires_at: string;
  firm_name: string | null;
}

type PageStatus =
  | "loading"
  | "ready"
  | "uploading"
  | "success"
  | "error"
  | "expired";

/**
 * Standalone document upload page — no authentication required.
 * Accessed via a secure token link sent by email.
 */
export default function TokenUploadPage() {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<PageStatus>("loading");
  const [info, setInfo] = useState<RequestInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch request info
  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/upload/${token}`);
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          const detail = data.detail || "Invalid or expired upload link";
          if (detail.includes("expired") || detail.includes("already")) {
            setStatus("expired");
          } else {
            setStatus("error");
          }
          setError(detail);
          return;
        }
        const data: RequestInfo = await res.json();
        setInfo(data);
        setStatus("ready");
      } catch {
        setError("Unable to load upload page. Please try again later.");
        setStatus("error");
      }
    })();
  }, [token]);

  const handleUpload = useCallback(
    async (file: File) => {
      if (!token || !info) return;
      setStatus("uploading");
      setProgress(10);

      try {
        // Step 1: Get presigned URL
        const presignRes = await fetch(`${API_BASE_URL}/upload/${token}/presign`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: file.name,
            mime_type: file.type || "application/octet-stream",
          }),
        });

        if (!presignRes.ok) {
          const data = await presignRes.json().catch(() => ({}));
          throw new Error(data.detail || "Failed to prepare upload");
        }

        const { upload_url, storage_key } = await presignRes.json();
        setProgress(30);

        // Step 2: Upload file directly to S3
        const uploadRes = await fetch(upload_url, {
          method: "PUT",
          headers: { "Content-Type": file.type || "application/octet-stream" },
          body: file,
        });

        if (!uploadRes.ok) {
          throw new Error("File upload failed. Please try again.");
        }
        setProgress(70);

        // Step 3: Register the upload
        const completeRes = await fetch(
          `${API_BASE_URL}/upload/${token}/complete`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              filename: file.name,
              storage_key,
              mime_type: file.type || "application/octet-stream",
              size_bytes: file.size,
            }),
          }
        );

        if (!completeRes.ok) {
          const data = await completeRes.json().catch(() => ({}));
          throw new Error(data.detail || "Failed to register document");
        }

        setProgress(100);
        setStatus("success");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
        setStatus("error");
      }
    },
    [token, info]
  );

  const onFileSelect = (file: File) => {
    setSelectedFile(file);
    setError(null);
  };

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) onFileSelect(file);
    },
    []
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDocType = (t: string) =>
    t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // ── Loading state ──
  if (status === "loading") {
    return (
      <div className="min-h-screen bg-[#f4f1ec] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin mx-auto mb-4 h-8 w-8 rounded-full border-4 border-gray-200 border-t-[#1a2332]" />
          <p className="text-gray-500">Loading upload page...</p>
        </div>
      </div>
    );
  }

  // ── Expired / Already uploaded ──
  if (status === "expired") {
    return (
      <div className="min-h-screen bg-[#f4f1ec] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-sm p-8 text-center">
          <div className="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Link Unavailable
          </h2>
          <p className="text-gray-500">{error}</p>
          <p className="text-sm text-gray-400 mt-4">
            Please contact the person who sent you this link for a new one.
          </p>
        </div>
      </div>
    );
  }

  // ── Error ──
  if (status === "error" && !info) {
    return (
      <div className="min-h-screen bg-[#f4f1ec] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-sm p-8 text-center">
          <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Something Went Wrong
          </h2>
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  // ── Success ──
  if (status === "success") {
    return (
      <div className="min-h-screen bg-[#f4f1ec] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-sm p-8 text-center">
          <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Document Uploaded Successfully
          </h2>
          <p className="text-gray-500 mb-2">
            Your document has been securely uploaded and{" "}
            <strong>{info?.requester_name}</strong> has been notified.
          </p>
          <p className="text-sm text-gray-400">
            You can safely close this page.
          </p>
        </div>
      </div>
    );
  }

  // ── Ready / Uploading ──
  return (
    <div className="min-h-screen bg-[#f4f1ec] flex items-center justify-center p-4">
      <div className="max-w-lg w-full">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-[#1a2332]">
            {info?.firm_name || "Estate Executor"}
          </h1>
          {info?.firm_name && (
            <p className="text-xs text-gray-400 uppercase tracking-wider mt-1">
              Powered by Estate Executor
            </p>
          )}
        </div>

        {/* Card */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          {/* Gold accent */}
          <div className="h-1 bg-gradient-to-r from-[#c9a84c] via-[#dfc373] to-[#c9a84c]" />

          <div className="p-8">
            <h2 className="text-xl font-semibold text-[#1a2332] mb-1">
              Upload Document
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              Requested by <strong>{info?.requester_name}</strong> for the{" "}
              <strong>Estate of {info?.decedent_name}</strong>
            </p>

            {/* Request details */}
            <div className="bg-[#f8f7f4] border-l-[3px] border-[#c9a84c] rounded-r-md p-4 mb-6">
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
                Requested Document
              </p>
              <p className="text-lg font-semibold text-[#1a2332]">
                {info ? formatDocType(info.doc_type_needed) : ""}
              </p>
              {info?.message && (
                <p className="text-sm text-gray-500 mt-2">{info.message}</p>
              )}
            </div>

            {/* Drop zone */}
            <div
              className={`
                relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                transition-colors duration-150
                ${
                  isDragging
                    ? "border-[#c9a84c] bg-amber-50"
                    : selectedFile
                      ? "border-green-300 bg-green-50"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                }
                ${status === "uploading" ? "pointer-events-none opacity-60" : ""}
              `}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onFileSelect(file);
                }}
              />

              {selectedFile ? (
                <div>
                  <svg className="w-10 h-10 text-green-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-sm font-medium text-gray-900">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {formatSize(selectedFile.size)}
                  </p>
                  <p className="text-xs text-gray-400 mt-2">
                    Click or drop to change file
                  </p>
                </div>
              ) : (
                <div>
                  <svg className="w-10 h-10 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="text-sm text-gray-500">
                    <span className="font-medium text-[#1a2332]">
                      Click to choose a file
                    </span>{" "}
                    or drag and drop
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    PDF, images, or other documents up to 50 MB
                  </p>
                </div>
              )}
            </div>

            {/* Progress bar */}
            {status === "uploading" && (
              <div className="mt-4">
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#c9a84c] rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-2 text-center">
                  Uploading securely...
                </p>
              </div>
            )}

            {/* Error message */}
            {status === "error" && error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-md">
                <p className="text-sm text-red-600">{error}</p>
                <button
                  className="text-sm text-red-700 underline mt-1"
                  onClick={() => {
                    setStatus("ready");
                    setError(null);
                  }}
                >
                  Try again
                </button>
              </div>
            )}

            {/* Upload button */}
            <button
              disabled={!selectedFile || status === "uploading"}
              onClick={() => selectedFile && handleUpload(selectedFile)}
              className={`
                mt-6 w-full py-3 px-4 rounded-md text-white font-semibold text-sm
                transition-colors duration-150
                ${
                  selectedFile && status !== "uploading"
                    ? "bg-[#1a2332] hover:bg-[#2a3342] cursor-pointer"
                    : "bg-gray-300 cursor-not-allowed"
                }
              `}
            >
              {status === "uploading" ? "Uploading..." : "Upload Document"}
            </button>
          </div>

          {/* Footer */}
          <div className="border-t border-gray-100 px-8 py-4 text-center">
            <p className="text-xs text-gray-400">
              Your document will be securely stored and only accessible to
              authorized parties.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
