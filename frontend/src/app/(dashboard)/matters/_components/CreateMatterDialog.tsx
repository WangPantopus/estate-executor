"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Check, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { useCreateMatter } from "@/hooks";
import {
  ESTATE_TYPE_LABELS,
  ASSET_TYPE_LABELS,
  MATTER_FLAGS,
  US_STATES,
} from "@/lib/constants";
import type { AssetType, EstateType, MatterCreate } from "@/lib/types";

// ─── Schema ──────────────────────────────────────────────────────────────────

const matterSchema = z.object({
  decedent_name: z.string().min(1, "Decedent name is required"),
  title: z.string().min(1, "Matter title is required"),
  estate_type: z.enum([
    "testate_probate",
    "intestate_probate",
    "trust_administration",
    "mixed_probate_trust",
    "conservatorship",
    "other",
  ] as const),
  jurisdiction_state: z.string().min(1, "Jurisdiction is required"),
  date_of_death: z.string().optional(),
  date_of_incapacity: z.string().optional(),
  estimated_value: z.number().nullable().optional(),
  asset_types_present: z.array(z.string()).optional(),
  flags: z.record(z.string(), z.boolean()).optional(),
});

type MatterFormData = z.infer<typeof matterSchema>;

const STEPS = [
  { label: "Basic Info", number: 1 },
  { label: "Asset Profile", number: 2 },
  { label: "Review", number: 3 },
] as const;

// ─── Dialog ──────────────────────────────────────────────────────────────────

interface CreateMatterDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
}

export function CreateMatterDialog({
  open,
  onOpenChange,
  firmId,
}: CreateMatterDialogProps) {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [success, setSuccess] = useState<{ matterId: string } | null>(null);
  const createMatter = useCreateMatter(firmId);

  const form = useForm<MatterFormData>({
    resolver: zodResolver(matterSchema),
    defaultValues: {
      decedent_name: "",
      title: "",
      estate_type: "testate_probate",
      jurisdiction_state: "",
      date_of_death: "",
      date_of_incapacity: "",
      estimated_value: null,
      asset_types_present: [],
      flags: {},
    },
  });

  const handleClose = useCallback(() => {
    if (success) {
      router.push(`/matters/${success.matterId}`);
    }
    onOpenChange(false);
    setTimeout(() => {
      setStep(1);
      setSuccess(null);
      form.reset();
    }, 200);
  }, [success, router, onOpenChange, form]);

  const canAdvance = useCallback(async () => {
    if (step === 1) {
      return form.trigger([
        "decedent_name",
        "title",
        "estate_type",
        "jurisdiction_state",
      ]);
    }
    return true;
  }, [step, form]);

  const handleNext = async () => {
    if (await canAdvance()) {
      setStep((s) => Math.min(s + 1, 3));
    }
  };

  const handleBack = () => setStep((s) => Math.max(s - 1, 1));

  const handleSubmit = async () => {
    const values = form.getValues();
    const payload: MatterCreate = {
      title: values.title,
      decedent_name: values.decedent_name,
      estate_type: values.estate_type as EstateType,
      jurisdiction_state: values.jurisdiction_state,
      date_of_death: values.date_of_death || undefined,
      date_of_incapacity: values.date_of_incapacity || undefined,
      estimated_value: values.estimated_value ?? undefined,
      asset_types_present: (values.asset_types_present ?? []) as AssetType[],
      flags: values.flags,
    };

    try {
      const matter = await createMatter.mutateAsync(payload);
      setSuccess({ matterId: matter.id });
    } catch {
      // Error handled by mutation state
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        {success ? (
          <SuccessView matterId={success.matterId} onClose={handleClose} />
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Create New Matter</DialogTitle>
              <DialogDescription>
                Set up a new estate administration case. The system will generate
                a customized task checklist based on your inputs.
              </DialogDescription>
            </DialogHeader>

            {/* Step indicator */}
            <StepIndicator currentStep={step} />

            <Separator />

            {/* Step content */}
            <div className="py-2">
              {step === 1 && <Step1BasicInfo form={form} />}
              {step === 2 && <Step2AssetProfile form={form} />}
              {step === 3 && <Step3Review form={form} />}
            </div>

            {/* Footer */}
            <Separator />
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="ghost"
                onClick={step === 1 ? handleClose : handleBack}
              >
                {step === 1 ? (
                  "Cancel"
                ) : (
                  <>
                    <ChevronLeft className="size-4" /> Back
                  </>
                )}
              </Button>

              {step < 3 ? (
                <Button onClick={handleNext}>
                  Next <ChevronRight className="size-4" />
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={createMatter.isPending}
                >
                  {createMatter.isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" /> Creating...
                    </>
                  ) : (
                    "Create Matter"
                  )}
                </Button>
              )}
            </div>

            {createMatter.isError && (
              <p className="text-xs text-danger mt-2">
                Failed to create matter. Please try again.
              </p>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ─── Step Indicator ──────────────────────────────────────────────────────────

function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex items-center justify-center gap-2 py-2">
      {STEPS.map((s, i) => (
        <div key={s.number} className="flex items-center gap-2">
          {i > 0 && (
            <div
              className={`h-px w-8 transition-colors ${
                currentStep > i ? "bg-primary" : "bg-border"
              }`}
            />
          )}
          <div className="flex items-center gap-1.5">
            <div
              className={`flex size-6 items-center justify-center rounded-full text-xs font-medium transition-colors ${
                currentStep > s.number
                  ? "bg-primary text-primary-foreground"
                  : currentStep === s.number
                    ? "bg-primary text-primary-foreground"
                    : "bg-surface-elevated text-muted-foreground"
              }`}
            >
              {currentStep > s.number ? (
                <Check className="size-3.5" />
              ) : (
                s.number
              )}
            </div>
            <span
              className={`text-xs ${
                currentStep === s.number
                  ? "font-medium text-foreground"
                  : "text-muted-foreground"
              }`}
            >
              {s.label}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Step 1: Basic Information ───────────────────────────────────────────────

function Step1BasicInfo({ form }: { form: UseFormReturn<MatterFormData> }) {
  const {
    register,
    setValue,
    watch,
    formState: { errors },
  } = form;

  const decedentName = watch("decedent_name");
  const estateType = watch("estate_type");

  const autoTitle = () => {
    if (decedentName && !form.getValues("title")) {
      setValue("title", `Estate of ${decedentName}`);
    }
  };

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Label htmlFor="decedent_name">Decedent Name *</Label>
        <Input
          id="decedent_name"
          placeholder="Full legal name"
          {...register("decedent_name", { onBlur: autoTitle })}
        />
        {errors.decedent_name && (
          <p className="text-xs text-danger">{errors.decedent_name.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="title">Matter Title *</Label>
        <Input
          id="title"
          placeholder='e.g., "Estate of John Smith"'
          {...register("title")}
        />
        {errors.title && (
          <p className="text-xs text-danger">{errors.title.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label>Estate Type *</Label>
        <Select
          value={estateType}
          onValueChange={(v) => setValue("estate_type", v as EstateType)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(ESTATE_TYPE_LABELS)
              .filter(([key]) => key !== "other")
              .map(([key, { label, description }]) => (
                <SelectItem key={key} value={key}>
                  <div>
                    <div>{label}</div>
                    <div className="text-xs text-muted-foreground">
                      {description}
                    </div>
                  </div>
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Jurisdiction *</Label>
        <Select
          value={watch("jurisdiction_state")}
          onValueChange={(v) => setValue("jurisdiction_state", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select state" />
          </SelectTrigger>
          <SelectContent>
            {US_STATES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {errors.jurisdiction_state && (
          <p className="text-xs text-danger">
            {errors.jurisdiction_state.message}
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="date_of_death">Date of Death</Label>
          <Input id="date_of_death" type="date" {...register("date_of_death")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="date_of_incapacity">Date of Incapacity</Label>
          <Input
            id="date_of_incapacity"
            type="date"
            {...register("date_of_incapacity")}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="estimated_value">Estimated Estate Value</Label>
        <CurrencyInput
          value={watch("estimated_value")}
          onChange={(v) => setValue("estimated_value", v)}
        />
      </div>
    </div>
  );
}

// ─── Step 2: Asset Profile ───────────────────────────────────────────────────

function Step2AssetProfile({ form }: { form: UseFormReturn<MatterFormData> }) {
  const assetTypes = form.watch("asset_types_present") ?? [];
  const flags = form.watch("flags") ?? {};

  const toggleAsset = (type: string) => {
    const current = form.getValues("asset_types_present") ?? [];
    if (current.includes(type)) {
      form.setValue(
        "asset_types_present",
        current.filter((t) => t !== type),
      );
    } else {
      form.setValue("asset_types_present", [...current, type]);
    }
  };

  const toggleFlag = (key: string) => {
    const current = form.getValues("flags") ?? {};
    form.setValue("flags", { ...current, [key]: !current[key] });
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-foreground mb-1">
          Asset Types Present
        </p>
        <p className="text-xs text-muted-foreground mb-3">
          Select all that apply. This helps generate a more accurate task
          checklist.
        </p>
        <div className="space-y-2">
          {Object.entries(ASSET_TYPE_LABELS)
            .filter(([key]) => key !== "receivable" && key !== "other")
            .map(([key, label]) => (
              <label
                key={key}
                className="flex items-center gap-3 rounded-md border border-border px-4 py-2.5 cursor-pointer transition-colors hover:bg-surface-elevated has-[:checked]:border-primary/30 has-[:checked]:bg-accent"
              >
                <input
                  type="checkbox"
                  checked={assetTypes.includes(key)}
                  onChange={() => toggleAsset(key)}
                  className="size-4 rounded border-border text-primary accent-primary"
                />
                <span className="text-sm">{label}</span>
              </label>
            ))}
        </div>
      </div>

      <Separator />

      <div>
        <p className="text-sm font-medium text-foreground mb-1">
          Additional Flags
        </p>
        <p className="text-xs text-muted-foreground mb-3">
          These flags trigger additional tasks and compliance requirements.
        </p>
        <div className="space-y-2">
          {MATTER_FLAGS.map((f) => (
            <label
              key={f.key}
              className="flex items-center gap-3 rounded-md border border-border px-4 py-2.5 cursor-pointer transition-colors hover:bg-surface-elevated has-[:checked]:border-primary/30 has-[:checked]:bg-accent"
            >
              <input
                type="checkbox"
                checked={!!flags[f.key]}
                onChange={() => toggleFlag(f.key)}
                className="size-4 rounded border-border text-primary accent-primary"
              />
              <span className="text-sm">{f.label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Step 3: Review ──────────────────────────────────────────────────────────

function Step3Review({ form }: { form: UseFormReturn<MatterFormData> }) {
  const values = form.getValues();
  const estateLabel =
    ESTATE_TYPE_LABELS[values.estate_type as EstateType]?.label ??
    values.estate_type;
  const stateLabel =
    US_STATES.find((s) => s.value === values.jurisdiction_state)?.label ??
    values.jurisdiction_state;
  const assetTypes = values.asset_types_present ?? [];
  const flags = values.flags ?? {};
  const activeFlags = MATTER_FLAGS.filter((f) => flags[f.key]);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-foreground mb-3">
          Basic Information
        </h3>
        <dl className="space-y-2 text-sm">
          <ReviewRow label="Matter Title" value={values.title} />
          <ReviewRow label="Decedent" value={values.decedent_name} />
          <ReviewRow label="Estate Type" value={estateLabel} />
          <ReviewRow label="Jurisdiction" value={stateLabel} />
          {values.date_of_death && (
            <ReviewRow label="Date of Death" value={values.date_of_death} />
          )}
          {values.date_of_incapacity && (
            <ReviewRow
              label="Date of Incapacity"
              value={values.date_of_incapacity}
            />
          )}
          {values.estimated_value && (
            <ReviewRow
              label="Estimated Value"
              value={`$${values.estimated_value.toLocaleString()}`}
            />
          )}
        </dl>
      </div>

      {(assetTypes.length > 0 || activeFlags.length > 0) && (
        <>
          <Separator />
          <div>
            <h3 className="text-sm font-medium text-foreground mb-3">
              Asset Profile
            </h3>
            {assetTypes.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {assetTypes.map((t) => (
                  <Badge key={t} variant="secondary">
                    {ASSET_TYPE_LABELS[t as AssetType] ?? t}
                  </Badge>
                ))}
              </div>
            )}
            {activeFlags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {activeFlags.map((f) => (
                  <Badge key={f.key} variant="warning">
                    {f.label}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <Separator />

      <div className="rounded-lg bg-surface-elevated p-4">
        <p className="text-sm text-muted-foreground leading-relaxed">
          The system will generate a customized task checklist and compliance
          calendar based on this information. You can always modify these later.
        </p>
      </div>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-right">{value}</dd>
    </div>
  );
}

// ─── Success View ────────────────────────────────────────────────────────────

function SuccessView({
  matterId,
  onClose,
}: {
  matterId: string;
  onClose: () => void;
}) {
  return (
    <div className="flex flex-col items-center py-8 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-success-light mb-4">
        <Check className="size-6 text-success" />
      </div>
      <h3 className="text-lg font-medium">Matter Created</h3>
      <p className="mt-2 text-sm text-muted-foreground max-w-sm">
        Your matter has been created and a customized task checklist has been
        generated. You can review and modify it on the matter dashboard.
      </p>
      <Button className="mt-6" onClick={onClose}>
        Go to Matter Dashboard
      </Button>
    </div>
  );
}

// ─── Currency Input ──────────────────────────────────────────────────────────

function CurrencyInput({
  value,
  onChange,
}: {
  value: number | null | undefined;
  onChange: (v: number | null) => void;
}) {
  const [display, setDisplay] = useState(
    value ? value.toLocaleString("en-US") : "",
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/[^0-9.]/g, "");
    setDisplay(raw);
    const num = parseFloat(raw);
    onChange(isNaN(num) ? null : num);
  };

  const handleBlur = () => {
    if (value) {
      setDisplay(value.toLocaleString("en-US"));
    }
  };

  return (
    <div className="relative">
      <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
        $
      </span>
      <Input
        value={display}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder="0"
        className="pl-7"
      />
    </div>
  );
}
