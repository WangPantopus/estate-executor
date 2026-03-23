"use client";

import { use, useState, useCallback } from "react";
import {
  FileText,
  Download,
  FileSpreadsheet,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/layout/Toaster";

const FIRM_ID = "current";

interface ReportDef {
  type: string;
  label: string;
  description: string;
  formats: string[];
  icon: typeof FileText;
}

const REPORTS: ReportDef[] = [
  {
    type: "matter-summary",
    label: "Matter Summary",
    description:
      "One-page PDF overview with matter details, stakeholders, task progress, asset summary, and upcoming deadlines. Suitable for court filing or client review.",
    formats: ["pdf"],
    icon: FileText,
  },
  {
    type: "asset-inventory",
    label: "Asset Inventory",
    description:
      "Full list of all assets with type, title, institution, ownership, values, and status. Includes summary totals. Suitable for court-filed inventory.",
    formats: ["pdf", "xlsx"],
    icon: FileText,
  },
  {
    type: "task-audit",
    label: "Task Completion Audit",
    description:
      "Every task with title, assigned to, status, completed date, and completed by. Timestamped and suitable for fiduciary defense.",
    formats: ["pdf", "xlsx"],
    icon: FileText,
  },
  {
    type: "distribution-ledger",
    label: "Distribution Ledger",
    description:
      "All distributions with date, beneficiary, amount, asset source, and acknowledgment status.",
    formats: ["pdf"],
    icon: FileText,
  },
  {
    type: "time-tracking",
    label: "Time Tracking Export",
    description:
      "Hours logged per professional per matter. Template with column headers ready for data entry.",
    formats: ["xlsx"],
    icon: FileSpreadsheet,
  },
];

type GeneratingState = Record<string, string | null>; // reportType-format -> "generating" | "done" | null

export default function ReportsPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);
  const { toast } = useToast();
  const [generating, setGenerating] = useState<GeneratingState>({});

  const handleGenerate = useCallback(
    async (reportType: string, format: string) => {
      const key = `${reportType}-${format}`;
      setGenerating((prev) => ({ ...prev, [key]: "generating" }));

      try {
        // Fetch the token
        let token: string | null = null;
        try {
          const res = await fetch("/auth/token");
          if (res.ok) {
            const data = await res.json();
            token = data.accessToken ?? null;
          }
        } catch {
          // proceed without token for dev
        }

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const url = `${apiUrl}/api/v1/firms/${FIRM_ID}/matters/${matterId}/reports/${reportType}?format=${format}`;

        const response = await fetch(url, {
          method: "POST",
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (!response.ok) {
          throw new Error(`Report generation failed (${response.status})`);
        }

        // Get filename from Content-Disposition header
        const disposition = response.headers.get("Content-Disposition");
        let filename = `${reportType}.${format}`;
        if (disposition) {
          const match = disposition.match(/filename="?([^"]+)"?/);
          if (match) filename = match[1];
        }

        // Download the file
        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = blobUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(blobUrl);

        setGenerating((prev) => ({ ...prev, [key]: "done" }));
        toast("success", `${REPORTS.find((r) => r.type === reportType)?.label || "Report"} downloaded`);

        // Reset the "done" state after 3 seconds
        setTimeout(() => {
          setGenerating((prev) => ({ ...prev, [key]: null }));
        }, 3000);
      } catch (err) {
        setGenerating((prev) => ({ ...prev, [key]: null }));
        toast(
          "error",
          `Failed to generate report: ${err instanceof Error ? err.message : "Unknown error"}`,
        );
      }
    },
    [matterId, toast],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        subtitle="Generate and download reports for this estate matter"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {REPORTS.map((report) => {
          const Icon = report.icon;

          return (
            <Card key={report.type} className="flex flex-col">
              <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                  <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="size-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base">{report.label}</CardTitle>
                    <div className="flex gap-1 mt-1">
                      {report.formats.map((fmt) => (
                        <Badge
                          key={fmt}
                          variant="muted"
                          className="text-[10px] uppercase"
                        >
                          {fmt}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col justify-between gap-4">
                <CardDescription className="text-xs leading-relaxed">
                  {report.description}
                </CardDescription>
                <div className="flex gap-2 flex-wrap">
                  {report.formats.map((fmt) => {
                    const key = `${report.type}-${fmt}`;
                    const state = generating[key];
                    const isGenerating = state === "generating";
                    const isDone = state === "done";

                    return (
                      <Button
                        key={fmt}
                        size="sm"
                        variant={isDone ? "outline" : "default"}
                        disabled={isGenerating}
                        onClick={() => handleGenerate(report.type, fmt)}
                        className="flex-1"
                      >
                        {isGenerating ? (
                          <>
                            <Loader2 className="size-3.5 mr-1 animate-spin" />
                            Generating...
                          </>
                        ) : isDone ? (
                          <>
                            <CheckCircle2 className="size-3.5 mr-1" />
                            Downloaded
                          </>
                        ) : (
                          <>
                            <Download className="size-3.5 mr-1" />
                            {fmt.toUpperCase()}
                          </>
                        )}
                      </Button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
