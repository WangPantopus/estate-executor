"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
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
import { Plus } from "lucide-react";
import type { Stakeholder, AssetListItem, DistributionType } from "@/lib/types";

interface RecordDistributionDialogProps {
  beneficiaries: Stakeholder[];
  assets: AssetListItem[];
  onSubmit: (data: {
    beneficiary_stakeholder_id: string;
    asset_id?: string | null;
    amount?: number | null;
    description: string;
    distribution_type: DistributionType;
    distribution_date: string;
    notes?: string | null;
  }) => Promise<void>;
  isPending: boolean;
}

const DISTRIBUTION_TYPES: { value: DistributionType; label: string }[] = [
  { value: "cash", label: "Cash" },
  { value: "asset_transfer", label: "Asset Transfer" },
  { value: "in_kind", label: "In Kind" },
];

export function RecordDistributionDialog({
  beneficiaries,
  assets,
  onSubmit,
  isPending,
}: RecordDistributionDialogProps) {
  const [open, setOpen] = useState(false);
  const [beneficiaryId, setBeneficiaryId] = useState("");
  const [assetId, setAssetId] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [distType, setDistType] = useState<DistributionType>("cash");
  const [distDate, setDistDate] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");

  const reset = () => {
    setBeneficiaryId("");
    setAssetId("");
    setAmount("");
    setDescription("");
    setDistType("cash");
    setDistDate(new Date().toISOString().split("T")[0]);
    setNotes("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit({
      beneficiary_stakeholder_id: beneficiaryId,
      asset_id: assetId || null,
      amount: amount ? parseFloat(amount) : null,
      description,
      distribution_type: distType,
      distribution_date: distDate,
      notes: notes || null,
    });
    reset();
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Plus className="size-4" />
          Record Distribution
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Record Distribution</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Beneficiary */}
          <div className="space-y-2">
            <Label htmlFor="beneficiary">Beneficiary</Label>
            <Select value={beneficiaryId} onValueChange={setBeneficiaryId}>
              <SelectTrigger>
                <SelectValue placeholder="Select beneficiary" />
              </SelectTrigger>
              <SelectContent>
                {beneficiaries.map((b) => (
                  <SelectItem key={b.id} value={b.id}>
                    {b.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Distribution type */}
          <div className="space-y-2">
            <Label htmlFor="dist-type">Distribution Type</Label>
            <Select
              value={distType}
              onValueChange={(v) => setDistType(v as DistributionType)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DISTRIBUTION_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount">Amount ($)</Label>
            <Input
              id="amount"
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>

          {/* Asset source */}
          <div className="space-y-2">
            <Label htmlFor="asset">Asset Source (optional)</Label>
            <Select value={assetId} onValueChange={setAssetId}>
              <SelectTrigger>
                <SelectValue placeholder="No specific asset" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">No specific asset</SelectItem>
                {assets.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.title}
                    {a.current_estimated_value
                      ? ` ($${a.current_estimated_value.toLocaleString()})`
                      : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              placeholder="e.g., Final cash distribution"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
          </div>

          {/* Date */}
          <div className="space-y-2">
            <Label htmlFor="date">Distribution Date</Label>
            <Input
              id="date"
              type="date"
              value={distDate}
              onChange={(e) => setDistDate(e.target.value)}
              required
            />
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes (optional)</Label>
            <Textarea
              id="notes"
              placeholder="Additional notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="resize-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!beneficiaryId || !description || isPending}>
              {isPending ? "Recording..." : "Record Distribution"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
