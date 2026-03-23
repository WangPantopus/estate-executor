"use client";

import { useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ENTITY_TYPE_LABELS, FUNDING_STATUS_LABELS, ASSET_TYPE_LABELS } from "@/lib/constants";
import { useCreateEntity } from "@/hooks";
import type { EntityCreate, AssetBrief } from "@/lib/types";

// ─── Schema ───────────────────────────────────────────────────────────────────

const entitySchema = z.object({
  entity_type: z.enum([
    "revocable_trust",
    "irrevocable_trust",
    "llc",
    "flp",
    "corporation",
    "foundation",
    "other",
  ] as const),
  name: z.string().min(1, "Name is required"),
  trustee: z.string().optional(),
  successor_trustee: z.string().optional(),
  funding_status: z.enum([
    "unknown",
    "fully_funded",
    "partially_funded",
    "unfunded",
  ] as const),
  asset_ids: z.array(z.string()),
  distribution_rules_text: z.string().optional(),
});

type EntityFormData = z.infer<typeof entitySchema>;

// ─── Dialog ───────────────────────────────────────────────────────────────────

interface CreateEntityDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
  matterId: string;
  unassignedAssets: AssetBrief[];
}

export function CreateEntityDialog({
  open,
  onOpenChange,
  firmId,
  matterId,
  unassignedAssets,
}: CreateEntityDialogProps) {
  const createEntity = useCreateEntity(firmId, matterId);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<EntityFormData>({
    resolver: zodResolver(entitySchema),
    defaultValues: {
      entity_type: "revocable_trust",
      name: "",
      trustee: "",
      successor_trustee: "",
      funding_status: "unknown",
      asset_ids: [],
      distribution_rules_text: "",
    },
  });

  const watchEntityType = watch("entity_type");
  const watchFunding = watch("funding_status");
  const watchAssetIds = watch("asset_ids");

  const handleClose = useCallback(() => {
    reset();
    onOpenChange(false);
  }, [reset, onOpenChange]);

  const onSubmit = async (data: EntityFormData) => {
    const payload: EntityCreate = {
      entity_type: data.entity_type,
      name: data.name,
      trustee: data.trustee || undefined,
      successor_trustee: data.successor_trustee || undefined,
      funding_status: data.funding_status,
      asset_ids: data.asset_ids.length > 0 ? data.asset_ids : undefined,
      distribution_rules: data.distribution_rules_text
        ? { description: data.distribution_rules_text }
        : undefined,
    };

    try {
      await createEntity.mutateAsync(payload);
      handleClose();
    } catch {
      // Error handled by mutation
    }
  };

  const toggleAsset = (assetId: string) => {
    const current = watchAssetIds;
    setValue(
      "asset_ids",
      current.includes(assetId)
        ? current.filter((id) => id !== assetId)
        : [...current, assetId],
    );
  };

  const isTrustType =
    watchEntityType === "revocable_trust" ||
    watchEntityType === "irrevocable_trust";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Entity</DialogTitle>
          <DialogDescription>
            Add a legal entity (trust, LLC, etc.) to the estate structure.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Entity type */}
          <div>
            <Label>
              Entity Type <span className="text-danger">*</span>
            </Label>
            <Select
              value={watchEntityType}
              onValueChange={(val) =>
                setValue("entity_type", val as EntityFormData["entity_type"])
              }
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(ENTITY_TYPE_LABELS).map(([key, label]) => (
                  <SelectItem key={key} value={key}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Name */}
          <div>
            <Label htmlFor="entity-name">
              Name <span className="text-danger">*</span>
            </Label>
            <Input
              id="entity-name"
              {...register("name")}
              placeholder={
                isTrustType
                  ? "e.g. The Smith Family Revocable Trust"
                  : "e.g. Smith Holdings LLC"
              }
              className="mt-1"
            />
            {errors.name && (
              <p className="text-xs text-danger mt-1">{errors.name.message}</p>
            )}
          </div>

          {/* Trustee fields (contextual for trusts) */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="trustee">
                {isTrustType ? "Trustee" : "Managing Member / Officer"}
              </Label>
              <Input
                id="trustee"
                {...register("trustee")}
                placeholder="Full name"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="successor_trustee">
                {isTrustType ? "Successor Trustee" : "Successor"}
              </Label>
              <Input
                id="successor_trustee"
                {...register("successor_trustee")}
                placeholder="Full name"
                className="mt-1"
              />
            </div>
          </div>

          {/* Funding status */}
          <div>
            <Label>Funding Status</Label>
            <Select
              value={watchFunding}
              onValueChange={(val) =>
                setValue("funding_status", val as EntityFormData["funding_status"])
              }
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(FUNDING_STATUS_LABELS).map(([key, label]) => (
                  <SelectItem key={key} value={key}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Link assets */}
          {unassignedAssets.length > 0 && (
            <div>
              <Label>Link Assets</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Select unassigned assets to link to this entity.
              </p>
              <div className="max-h-48 overflow-y-auto rounded-md border border-border p-2 space-y-1">
                {unassignedAssets.map((asset) => (
                  <label
                    key={asset.id}
                    className="flex items-center gap-2 text-sm cursor-pointer hover:bg-surface-elevated rounded px-2 py-1.5"
                  >
                    <input
                      type="checkbox"
                      checked={watchAssetIds.includes(asset.id)}
                      onChange={() => toggleAsset(asset.id)}
                      className="size-3.5 rounded border-border text-primary focus:ring-primary/40"
                    />
                    <div className="flex-1 min-w-0">
                      <span className="truncate text-foreground">{asset.title}</span>
                      <span className="text-xs text-muted-foreground ml-1.5 capitalize">
                        ({ASSET_TYPE_LABELS[asset.asset_type]})
                      </span>
                    </div>
                    {asset.current_estimated_value !== null && (
                      <span className="text-xs tabular-nums text-muted-foreground shrink-0">
                        ${asset.current_estimated_value.toLocaleString()}
                      </span>
                    )}
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Distribution rules */}
          <div>
            <Label htmlFor="distribution_rules">Distribution Rules</Label>
            <Textarea
              id="distribution_rules"
              {...register("distribution_rules_text")}
              placeholder="Describe distribution provisions, e.g. 'Equal shares to children upon reaching age 25...'"
              rows={3}
              className="mt-1"
            />
          </div>

          {/* Error */}
          {createEntity.error && (
            <p className="text-sm text-danger">
              Failed to create entity. Please try again.
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createEntity.isPending}>
              {createEntity.isPending && (
                <Loader2 className="size-4 mr-1 animate-spin" />
              )}
              Create Entity
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
