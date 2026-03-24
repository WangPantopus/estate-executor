"use client";

import React, { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useCreateTimeEntry } from "@/hooks";
import type { Task } from "@/lib/types";

interface LogTimeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
  matterId: string;
  tasks: Task[];
  preselectedTaskId?: string | null;
}

export function LogTimeDialog({
  open,
  onOpenChange,
  firmId,
  matterId,
  tasks,
  preselectedTaskId,
}: LogTimeDialogProps) {
  const createEntry = useCreateTimeEntry(firmId, matterId);
  const [taskId, setTaskId] = useState(preselectedTaskId || "");

  // Sync preselectedTaskId when dialog opens with a new task
  useEffect(() => {
    if (open) {
      setTaskId(preselectedTaskId || "");
    }
  }, [open, preselectedTaskId]);
  const [hours, setHours] = useState("0");
  const [minutes, setMinutes] = useState("0");
  const [description, setDescription] = useState("");
  const [entryDate, setEntryDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [billable, setBillable] = useState(true);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const h = parseInt(hours) || 0;
    const m = parseInt(minutes) || 0;
    if (h === 0 && m === 0) return;

    await createEntry.mutateAsync({
      task_id: taskId || undefined,
      hours: h,
      minutes: m,
      description,
      entry_date: entryDate,
      billable,
    });

    // Reset and close
    setTaskId(preselectedTaskId || "");
    setHours("0");
    setMinutes("0");
    setDescription("");
    setBillable(true);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Log Time</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Task selector */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              Task (optional)
            </label>
            <select
              className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
            >
              <option value="">General / No specific task</option>
              {tasks.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title}
                </option>
              ))}
            </select>
          </div>

          {/* Time inputs */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Hours
              </label>
              <Input
                type="number"
                min="0"
                max="24"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Minutes
              </label>
              <Input
                type="number"
                min="0"
                max="59"
                value={minutes}
                onChange={(e) => setMinutes(e.target.value)}
              />
            </div>
          </div>

          {/* Date */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              Date
            </label>
            <Input
              type="date"
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              Description
            </label>
            <textarea
              className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm min-h-[60px] resize-y"
              placeholder="What did you work on?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
          </div>

          {/* Billable toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={billable}
              onChange={(e) => setBillable(e.target.checked)}
              className="size-4 rounded border-border text-primary focus:ring-primary/40"
            />
            <span className="text-sm">Billable</span>
          </label>

          {/* Submit */}
          <Button
            type="submit"
            className="w-full"
            disabled={
              createEntry.isPending ||
              (!parseInt(hours) && !parseInt(minutes)) ||
              !description.trim()
            }
          >
            {createEntry.isPending ? (
              <Loader2 className="size-4 mr-1 animate-spin" />
            ) : null}
            Log Time
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
