"use client";

import { useState, useEffect } from "react";
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
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

interface WaiveTaskDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  taskTitle: string;
  isPending: boolean;
  onConfirm: (reason: string) => void;
}

export function WaiveTaskDialog({
  open,
  onOpenChange,
  taskTitle,
  isPending,
  onConfirm,
}: WaiveTaskDialogProps) {
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (!open) setReason(""); // eslint-disable-line react-hooks/set-state-in-effect -- reset form on close
  }, [open]);

  const handleConfirm = () => {
    if (reason.trim()) {
      onConfirm(reason.trim());
      setReason("");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Waive Task</DialogTitle>
          <DialogDescription>
            Waive &ldquo;{taskTitle}&rdquo;? This marks the task as not applicable. A reason is required.
          </DialogDescription>
        </DialogHeader>

        <div>
          <Label htmlFor="waive-reason">
            Reason <span className="text-danger">*</span>
          </Label>
          <Textarea
            id="waive-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why this task is being waived..."
            rows={3}
            className="mt-1"
          />
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!reason.trim() || isPending}
          >
            {isPending && <Loader2 className="size-4 mr-1 animate-spin" />}
            Waive Task
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
