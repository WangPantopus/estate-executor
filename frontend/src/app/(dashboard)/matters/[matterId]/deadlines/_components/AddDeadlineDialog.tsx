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
import { useCreateDeadline } from "@/hooks";
import type { Stakeholder, Task, DeadlineCreate } from "@/lib/types";

// ─── Schema ───────────────────────────────────────────────────────────────────

const deadlineSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  due_date: z.string().min(1, "Due date is required"),
  assigned_to: z.string().optional(),
  task_id: z.string().optional(),
  reminder_30: z.boolean(),
  reminder_14: z.boolean(),
  reminder_7: z.boolean(),
  reminder_3: z.boolean(),
  reminder_1: z.boolean(),
});

type DeadlineFormData = z.infer<typeof deadlineSchema>;

// ─── Dialog ───────────────────────────────────────────────────────────────────

interface AddDeadlineDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
  matterId: string;
  stakeholders: Stakeholder[];
  tasks: Task[];
}

export function AddDeadlineDialog({
  open,
  onOpenChange,
  firmId,
  matterId,
  stakeholders,
  tasks,
}: AddDeadlineDialogProps) {
  const createDeadline = useCreateDeadline(firmId, matterId);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<DeadlineFormData>({
    resolver: zodResolver(deadlineSchema),
    defaultValues: {
      title: "",
      description: "",
      due_date: "",
      assigned_to: "",
      task_id: "",
      reminder_30: true,
      reminder_14: false,
      reminder_7: true,
      reminder_3: false,
      reminder_1: true,
    },
  });

  const watchAssigned = watch("assigned_to");
  const watchTask = watch("task_id");

  const handleClose = useCallback(() => {
    reset();
    onOpenChange(false);
  }, [reset, onOpenChange]);

  const onSubmit = async (data: DeadlineFormData) => {
    const daysBefore: number[] = [];
    if (data.reminder_30) daysBefore.push(30);
    if (data.reminder_14) daysBefore.push(14);
    if (data.reminder_7) daysBefore.push(7);
    if (data.reminder_3) daysBefore.push(3);
    if (data.reminder_1) daysBefore.push(1);

    const payload: DeadlineCreate = {
      title: data.title,
      description: data.description || undefined,
      due_date: data.due_date,
      assigned_to: data.assigned_to || null,
      task_id: data.task_id || null,
      reminder_config: { days_before: daysBefore },
    };

    try {
      await createDeadline.mutateAsync(payload);
      handleClose();
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Deadline</DialogTitle>
          <DialogDescription>
            Create a manual compliance deadline.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Title */}
          <div>
            <Label htmlFor="dl-title">
              Title <span className="text-danger">*</span>
            </Label>
            <Input
              id="dl-title"
              {...register("title")}
              placeholder="e.g. Federal Estate Tax Return Due"
              className="mt-1"
            />
            {errors.title && (
              <p className="text-xs text-danger mt-1">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <Label htmlFor="dl-desc">Description</Label>
            <Textarea
              id="dl-desc"
              {...register("description")}
              placeholder="Additional details..."
              rows={2}
              className="mt-1"
            />
          </div>

          {/* Due date */}
          <div>
            <Label htmlFor="dl-date">
              Due Date <span className="text-danger">*</span>
            </Label>
            <Input
              id="dl-date"
              type="date"
              {...register("due_date")}
              className="mt-1"
            />
            {errors.due_date && (
              <p className="text-xs text-danger mt-1">{errors.due_date.message}</p>
            )}
          </div>

          {/* Assign to */}
          <div>
            <Label>Assign To</Label>
            <Select
              value={watchAssigned || "__none__"}
              onValueChange={(v) => setValue("assigned_to", v === "__none__" ? "" : v)}
            >
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Unassigned" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">Unassigned</SelectItem>
                {stakeholders.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Link to task */}
          {tasks.length > 0 && (
            <div>
              <Label>Link to Task</Label>
              <Select
                value={watchTask || "__none__"}
                onValueChange={(v) => setValue("task_id", v === "__none__" ? "" : v)}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">None</SelectItem>
                  {tasks.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Reminders */}
          <div>
            <Label>Reminders</Label>
            <div className="flex flex-wrap gap-3 mt-2">
              {([
                { field: "reminder_30" as const, label: "30 days" },
                { field: "reminder_14" as const, label: "14 days" },
                { field: "reminder_7" as const, label: "7 days" },
                { field: "reminder_3" as const, label: "3 days" },
                { field: "reminder_1" as const, label: "1 day" },
              ]).map(({ field, label }) => (
                <label key={field} className="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    {...register(field)}
                    className="size-3.5 rounded border-border text-primary focus:ring-primary/40"
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          {/* Error */}
          {createDeadline.error && (
            <p className="text-sm text-danger">Failed to create deadline.</p>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createDeadline.isPending}>
              {createDeadline.isPending && (
                <Loader2 className="size-4 mr-1 animate-spin" />
              )}
              Add Deadline
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
