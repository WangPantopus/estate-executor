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
import {
  ASSET_TYPE_LABELS,
  OWNERSHIP_TYPE_LABELS,
  TRANSFER_MECHANISM_LABELS,
} from "@/lib/constants";
import { useCreateAsset } from "@/hooks";
import type { AssetCreate, AssetType } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ASSET_TYPE_ICONS, ASSET_TYPE_COLORS } from "./AssetCard";

// Types that typically have institution/account fields
const ACCOUNT_TYPES: AssetType[] = [
  "bank_account",
  "brokerage_account",
  "retirement_account",
  "life_insurance",
];

// ─── Schema ───────────────────────────────────────────────────────────────────

const assetSchema = z.object({
  asset_type: z.enum([
    "real_estate",
    "bank_account",
    "brokerage_account",
    "retirement_account",
    "life_insurance",
    "business_interest",
    "vehicle",
    "digital_asset",
    "personal_property",
    "receivable",
    "other",
  ] as const),
  title: z.string().min(1, "Title is required"),
  institution: z.string().optional(),
  account_number: z.string().optional(),
  description: z.string().optional(),
  ownership_type: z.string().optional(),
  transfer_mechanism: z.string().optional(),
  current_estimated_value: z.number().nullable().optional(),
});

type AssetFormData = z.infer<typeof assetSchema>;

// ─── Dialog ───────────────────────────────────────────────────────────────────

interface AddAssetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
  matterId: string;
}

export function AddAssetDialog({
  open,
  onOpenChange,
  firmId,
  matterId,
}: AddAssetDialogProps) {
  const createAsset = useCreateAsset(firmId, matterId);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<AssetFormData>({
    resolver: zodResolver(assetSchema),
    defaultValues: {
      asset_type: "bank_account",
      title: "",
      institution: "",
      account_number: "",
      description: "",
      ownership_type: "",
      transfer_mechanism: "",
      current_estimated_value: null,
    },
  });

  const watchAssetType = watch("asset_type");
  const watchOwnership = watch("ownership_type");
  const watchTransfer = watch("transfer_mechanism");
  const showAccountFields = ACCOUNT_TYPES.includes(watchAssetType);

  const handleClose = useCallback(() => {
    reset();
    onOpenChange(false);
  }, [reset, onOpenChange]);

  const onSubmit = async (data: AssetFormData) => {
    const payload: AssetCreate = {
      asset_type: data.asset_type,
      title: data.title,
      description: data.description || undefined,
      institution: data.institution || undefined,
      account_number: data.account_number || undefined,
      ownership_type: data.ownership_type
        ? (data.ownership_type as AssetCreate["ownership_type"])
        : undefined,
      transfer_mechanism: data.transfer_mechanism
        ? (data.transfer_mechanism as AssetCreate["transfer_mechanism"])
        : undefined,
      current_estimated_value: data.current_estimated_value,
    };

    try {
      await createAsset.mutateAsync(payload);
      handleClose();
    } catch {
      // Error handled by mutation
    }
  };

  // Handle currency input - strip formatting for storage
  const handleValueChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/[^0-9.]/g, "");
    const num = parseFloat(raw);
    setValue("current_estimated_value", isNaN(num) ? null : num);
  };

  const currentValue = watch("current_estimated_value");
  const displayValue =
    currentValue !== null && currentValue !== undefined
      ? currentValue.toLocaleString("en-US")
      : "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Asset</DialogTitle>
          <DialogDescription>
            Register a new asset in the estate inventory.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Asset type selector - icon grid */}
          <div>
            <Label>
              Asset Type <span className="text-danger">*</span>
            </Label>
            <div className="grid grid-cols-4 gap-2 mt-2">
              {(Object.entries(ASSET_TYPE_LABELS) as [AssetType, string][]).map(
                ([type, label]) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setValue("asset_type", type)}
                    className={cn(
                      "flex flex-col items-center gap-1 rounded-lg border p-2.5 transition-all text-center",
                      watchAssetType === type
                        ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                        : "border-border hover:border-primary/30",
                    )}
                  >
                    <div
                      className={cn(
                        "flex items-center justify-center size-8 rounded-md",
                        ASSET_TYPE_COLORS[type],
                      )}
                    >
                      {ASSET_TYPE_ICONS[type]}
                    </div>
                    <span className="text-[10px] leading-tight text-foreground">
                      {label.split(" ")[0]}
                    </span>
                  </button>
                ),
              )}
            </div>
          </div>

          {/* Title */}
          <div>
            <Label htmlFor="title">
              Title <span className="text-danger">*</span>
            </Label>
            <Input
              id="title"
              {...register("title")}
              placeholder="e.g. Chase Checking Account, 123 Main St"
              className="mt-1"
            />
            {errors.title && (
              <p className="text-xs text-danger mt-1">{errors.title.message}</p>
            )}
          </div>

          {/* Institution & Account Number (conditional) */}
          {showAccountFields && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="institution">Institution</Label>
                <Input
                  id="institution"
                  {...register("institution")}
                  placeholder="e.g. Chase, Fidelity"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="account_number">Account Number</Label>
                <Input
                  id="account_number"
                  {...register("account_number")}
                  placeholder="Last 4 digits"
                  className="mt-1 font-mono"
                  maxLength={20}
                />
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  Will be masked in display
                </p>
              </div>
            </div>
          )}
          {!showAccountFields && (
            <div>
              <Label htmlFor="institution">Institution / Location</Label>
              <Input
                id="institution"
                {...register("institution")}
                placeholder="Optional"
                className="mt-1"
              />
            </div>
          )}

          {/* Ownership & Transfer */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Ownership Type</Label>
              <Select
                value={watchOwnership || "__none__"}
                onValueChange={(val) =>
                  setValue("ownership_type", val === "__none__" ? "" : val)
                }
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Not specified</SelectItem>
                  {Object.entries(OWNERSHIP_TYPE_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Transfer Mechanism</Label>
              <Select
                value={watchTransfer || "__none__"}
                onValueChange={(val) =>
                  setValue("transfer_mechanism", val === "__none__" ? "" : val)
                }
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Not specified</SelectItem>
                  {Object.entries(TRANSFER_MECHANISM_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Estimated value */}
          <div>
            <Label htmlFor="value">Estimated Value</Label>
            <div className="relative mt-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                $
              </span>
              <Input
                id="value"
                value={displayValue}
                onChange={handleValueChange}
                placeholder="0"
                className="pl-7 tabular-nums"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register("description")}
              placeholder="Additional details about this asset..."
              rows={3}
              className="mt-1"
            />
          </div>

          {/* Error */}
          {createAsset.error && (
            <p className="text-sm text-danger">
              Failed to create asset. Please try again.
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createAsset.isPending}>
              {createAsset.isPending && (
                <Loader2 className="size-4 mr-1 animate-spin" />
              )}
              Add Asset
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
