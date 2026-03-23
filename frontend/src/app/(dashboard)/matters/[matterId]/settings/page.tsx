"use client";

import { use, useState } from "react";
import {
  Loader2,
  AlertTriangle,
  Archive,
  Lock,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import {
  useMatterDashboard,
  useUpdateMatter,
  useCloseMatter,
  useStakeholders,
} from "@/hooks";
import { ESTATE_TYPE_LABELS, US_STATES } from "@/lib/constants";
import { AIUsageDashboard } from "./_components/AIUsageDashboard";

// ─── Constants ────────────────────────────────────────────────────────────────

const FIRM_ID = "current";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MatterSettingsPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);
  const router = useRouter();

  const { data: dashboard, isLoading } = useMatterDashboard(FIRM_ID, matterId);
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);
  const updateMatter = useUpdateMatter(FIRM_ID, matterId);
  const closeMatter = useCloseMatter(FIRM_ID, matterId);

  const [editingTitle, setEditingTitle] = useState(false);
  const [titleValue, setTitleValue] = useState("");
  const [editingValue, setEditingValue] = useState(false);
  const [valueInput, setValueInput] = useState("");

  const stakeholders = stakeholdersData?.data ?? [];

  if (isLoading) {
    return <LoadingState variant="detail" />;
  }

  if (!dashboard) {
    return (
      <div className="py-12 text-center">
        <p className="text-danger">Failed to load matter settings.</p>
      </div>
    );
  }

  const { matter } = dashboard;
  const isClosed = matter.status === "closed" || matter.status === "archived";
  const stateName = US_STATES.find((s) => s.value === matter.jurisdiction_state)?.label ?? matter.jurisdiction_state;
  const estateLabel = ESTATE_TYPE_LABELS[matter.estate_type]?.label ?? matter.estate_type;

  const handleTitleSave = () => {
    if (titleValue.trim()) {
      updateMatter.mutate(
        { title: titleValue.trim() },
        { onSuccess: () => setEditingTitle(false) },
      );
    }
  };

  const handleValueSave = () => {
    const num = parseFloat(valueInput.replace(/[,$]/g, ""));
    updateMatter.mutate(
      { estimated_value: isNaN(num) ? null : num },
      { onSuccess: () => setEditingValue(false) },
    );
  };

  const handleClose = () => {
    if (confirm("Close this matter? This marks it as complete. You can archive it later.")) {
      closeMatter.mutate(undefined, {
        onSuccess: () => router.push(`/matters/${matterId}`),
      });
    }
  };

  const handleArchive = () => {
    if (confirm("Archive this matter? It will be hidden from the active matters list.")) {
      updateMatter.mutate({ status: "archived" });
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader title="Matter Settings" />

      {/* Matter details */}
      <Card>
        <CardContent className="p-6 space-y-5">
          {/* Title */}
          <div>
            <Label>Matter Title</Label>
            {editingTitle ? (
              <div className="flex items-center gap-2 mt-1">
                <Input
                  value={titleValue}
                  onChange={(e) => setTitleValue(e.target.value)}
                  className="max-w-md"
                />
                <Button size="sm" onClick={handleTitleSave} disabled={updateMatter.isPending}>
                  {updateMatter.isPending ? <Loader2 className="size-4 animate-spin" /> : "Save"}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditingTitle(false)}>Cancel</Button>
              </div>
            ) : (
              <div className="flex items-center gap-2 mt-1">
                <p className="text-sm text-foreground">{matter.title}</p>
                {!isClosed && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => { setTitleValue(matter.title); setEditingTitle(true); }}
                  >
                    Edit
                  </Button>
                )}
              </div>
            )}
          </div>

          <Separator />

          {/* Locked fields */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="flex items-center gap-1">
                Estate Type
                <Lock className="size-3 text-muted-foreground" />
              </Label>
              <p className="text-sm text-foreground mt-1">{estateLabel}</p>
              <p className="text-xs text-muted-foreground">Locked after task generation</p>
            </div>
            <div>
              <Label className="flex items-center gap-1">
                Jurisdiction
                <Lock className="size-3 text-muted-foreground" />
              </Label>
              <p className="text-sm text-foreground mt-1">{stateName}</p>
              <p className="text-xs text-muted-foreground">Locked after task generation</p>
            </div>
          </div>

          <Separator />

          {/* Decedent name */}
          <div>
            <Label>Decedent Name</Label>
            <p className="text-sm text-foreground mt-1">{matter.decedent_name}</p>
          </div>

          {/* Date of death */}
          <div>
            <Label>Date of Death</Label>
            <p className="text-sm text-foreground mt-1">
              {matter.date_of_death
                ? new Date(matter.date_of_death + "T00:00:00").toLocaleDateString("en-US", {
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })
                : "Not specified"}
            </p>
          </div>

          <Separator />

          {/* Estimated value */}
          <div>
            <Label>Estimated Value</Label>
            {editingValue ? (
              <div className="flex items-center gap-2 mt-1">
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                  <Input
                    value={valueInput}
                    onChange={(e) => setValueInput(e.target.value)}
                    className="pl-7 max-w-[200px]"
                  />
                </div>
                <Button size="sm" onClick={handleValueSave} disabled={updateMatter.isPending}>
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditingValue(false)}>Cancel</Button>
              </div>
            ) : (
              <div className="flex items-center gap-2 mt-1">
                <p className="text-sm text-foreground tabular-nums">
                  {matter.estimated_value !== null
                    ? `$${matter.estimated_value.toLocaleString()}`
                    : "Not specified"}
                </p>
                {!isClosed && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setValueInput(matter.estimated_value?.toString() ?? "");
                      setEditingValue(true);
                    }}
                  >
                    Edit
                  </Button>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Stakeholders link */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-foreground">Stakeholders</h3>
              <p className="text-xs text-muted-foreground">{stakeholders.length} stakeholder{stakeholders.length !== 1 ? "s" : ""}</p>
            </div>
            <Button variant="outline" size="sm" asChild>
              <a href={`/matters/${matterId}/communications`}>Manage</a>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* AI Usage Dashboard */}
      <AIUsageDashboard firmId={FIRM_ID} matterId={matterId} />

      {/* Danger zone */}
      <Card className="border-danger/30">
        <CardContent className="p-6">
          <h3 className="text-sm font-medium text-danger mb-4 flex items-center gap-1.5">
            <AlertTriangle className="size-4" />
            Danger Zone
          </h3>

          <div className="space-y-4">
            {/* Close matter */}
            {matter.status === "active" && (
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Close Matter</p>
                  <p className="text-xs text-muted-foreground">
                    Mark as complete. Validates all required tasks are done.
                  </p>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleClose}
                  disabled={closeMatter.isPending}
                >
                  {closeMatter.isPending && <Loader2 className="size-4 mr-1 animate-spin" />}
                  Close Matter
                </Button>
              </div>
            )}

            {/* Archive */}
            {matter.status === "closed" && (
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Archive Matter</p>
                  <p className="text-xs text-muted-foreground">
                    Hide from active matters list. Data is retained.
                  </p>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleArchive}
                  disabled={updateMatter.isPending}
                >
                  <Archive className="size-4 mr-1" />
                  Archive
                </Button>
              </div>
            )}

            {matter.status === "archived" && (
              <p className="text-sm text-muted-foreground">This matter is archived.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
