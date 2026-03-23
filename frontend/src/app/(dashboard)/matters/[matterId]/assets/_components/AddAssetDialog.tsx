"use client";

import { useCallback, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Sparkles } from "lucide-react";
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
import { useCreateAsset, useApi } from "@/hooks";
import type { AssetCreate, AssetType } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ASSET_TYPE_ICONS, ASSET_TYPE_COLORS } from "./AssetCard";

// ─── Prefill mapping from AI extracted data ──────────────────────────────────

/** Maps doc_type to asset_type for prefill */
const DOC_TYPE_TO_ASSET_TYPE: Record<string, AssetType> = {
  account_statement: "bank_account",
  deed: "real_estate",
  insurance_policy: "life_insurance",
  appraisal: "real_estate",
};

export interface AssetPrefillData {
  /** Source document type that was classified */
  docType: string;
  /** AI-extracted fields to prefill the form */
  extractedData: Record<string, unknown>;
  /** Document ID to link after creation */
  documentId?: string;
}

function buildPrefillDefaults(prefill: AssetPrefillData): Partial<AssetFormData> {
  const data = prefill.extractedData;
  const defaults: Partial<AssetFormData> = {};

  // Map doc_type to asset_type
  const assetType = DOC_TYPE_TO_ASSET_TYPE[prefill.docType];
  if (assetType) defaults.asset_type = assetType;

  // Common field mappings
  if (typeof data.institution === "string") defaults.institution = data.institution;
  if (typeof data.carrier === "string") defaults.institution = data.carrier;

  // Account number (last 4)
  if (typeof data.account_number_last4 === "string") defaults.account_number = data.account_number_last4;
  if (typeof data.policy_number === "string") defaults.account_number = data.policy_number;

  // Value fields
  if (typeof data.balance === "number") defaults.current_estimated_value = data.balance;
  if (typeof data.face_value === "number") defaults.current_estimated_value = data.face_value;
  if (typeof data.appraised_value === "number") defaults.current_estimated_value = data.appraised_value;

  // Title generation
  if (prefill.docType === "account_statement") {
    const inst = (data.institution as string) || "";
    const type = (data.account_type as string) || "Account";
    defaults.title = inst ? `${inst} ${type}` : type;
  } else if (prefill.docType === "deed") {
    defaults.title = (data.property_address as string) || "Real Property";
  } else if (prefill.docType === "insurance_policy") {
    const carrier = (data.carrier as string) || "";
    const policyType = (data.policy_type as string) || "Life";
    defaults.title = carrier ? `${carrier} ${policyType} Policy` : `${policyType} Insurance Policy`;
  } else if (prefill.docType === "appraisal") {
    defaults.title = (data.property_description as string) || "Appraised Property";
  }

  // Description from remaining fields
  const descParts: string[] = [];
  if (typeof data.property_address === "string") descParts.push(`Address: ${data.property_address}`);
  if (typeof data.beneficiary_name === "string") descParts.push(`Beneficiary: ${data.beneficiary_name}`);
  if (typeof data.as_of_date === "string") descParts.push(`As of: ${data.as_of_date}`);
  if (typeof data.appraiser_name === "string") descParts.push(`Appraiser: ${data.appraiser_name}`);
  if (typeof data.appraisal_date === "string") descParts.push(`Appraisal date: ${data.appraisal_date}`);
  if (typeof data.grantee === "string") descParts.push(`Grantee: ${data.grantee}`);
  if (typeof data.parcel_number === "string") descParts.push(`Parcel: ${data.parcel_number}`);
  if (descParts.length > 0) defaults.description = descParts.join("\n");

  return defaults;
}

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
  /** Optional prefill data from AI extraction */
  prefill?: AssetPrefillData | null;
}

export function AddAssetDialog({
  open,
  onOpenChange,
  firmId,
  matterId,
  prefill,
}: AddAssetDialogProps) {
  const createAsset = useCreateAsset(firmId, matterId);
  const api = useApi();

  const defaultValues: AssetFormData = {
    asset_type: "bank_account",
    title: "",
    institution: "",
    account_number: "",
    description: "",
    ownership_type: "",
    transfer_mechanism: "",
    current_estimated_value: null,
  };

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<AssetFormData>({
    resolver: zodResolver(assetSchema),
    defaultValues,
  });

  // Apply prefill data when dialog opens with prefill
  useEffect(() => {
    if (open && prefill) {
      const prefillDefaults = buildPrefillDefaults(prefill);
      // Reset with merged defaults
      reset({ ...defaultValues, ...prefillDefaults });
    } else if (open && !prefill) {
      reset(defaultValues);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, prefill]);

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
      const newAsset = await createAsset.mutateAsync(payload);
      // If this was created from a document, link the document to the new asset
      if (prefill?.documentId && newAsset?.id) {
        try {
          await api.linkAssetDocument(firmId, matterId, newAsset.id, {
            document_id: prefill.documentId,
          });
        } catch {
          // Non-critical — asset was created, linking just failed
        }
      }
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
          <DialogTitle>
            {prefill ? "Create Asset from Document" : "Add Asset"}
          </DialogTitle>
          <DialogDescription>
            {prefill
              ? "Review the pre-filled data from AI extraction, edit as needed, then confirm."
              : "Register a new asset in the estate inventory."}
          </DialogDescription>
        </DialogHeader>
        {prefill && (
          <div className="rounded-md border border-info/30 bg-info-light/30 px-3 py-2 flex items-center gap-2">
            <Sparkles className="size-3.5 text-info shrink-0" />
            <span className="text-xs text-info">
              Fields pre-filled from AI-extracted data. Please review before saving.
            </span>
          </div>
        )}

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
