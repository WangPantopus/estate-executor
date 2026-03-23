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
import { TASK_PHASE_LABELS, TASK_PRIORITY_LABELS } from "@/lib/constants";
import { useCreateTask } from "@/hooks";
import type { Task, Stakeholder, TaskCreate } from "@/lib/types";

// ─── Schema ───────────────────────────────────────────────────────────────────

const taskSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  instructions: z.string().optional(),
  phase: z.enum([
    "immediate",
    "asset_inventory",
    "notification",
    "probate_filing",
    "tax",
    "transfer_distribution",
    "family_communication",
    "closing",
    "custom",
  ] as const),
  priority: z.enum(["critical", "normal", "informational"] as const),
  assigned_to: z.string().optional(),
  due_date: z.string().optional(),
  requires_document: z.boolean(),
  dependency_ids: z.array(z.string()),
});

type TaskFormData = z.infer<typeof taskSchema>;

// ─── Dialog ───────────────────────────────────────────────────────────────────

interface CreateTaskDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
  matterId: string;
  tasks: Task[];
  stakeholders: Stakeholder[];
}

export function CreateTaskDialog({
  open,
  onOpenChange,
  firmId,
  matterId,
  tasks,
  stakeholders,
}: CreateTaskDialogProps) {
  const createTask = useCreateTask(firmId, matterId);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<TaskFormData>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: "",
      description: "",
      instructions: "",
      phase: "custom",
      priority: "normal",
      assigned_to: "",
      due_date: "",
      requires_document: false,
      dependency_ids: [],
    },
  });

  const watchPhase = watch("phase");
  const watchPriority = watch("priority");
  const watchAssignedTo = watch("assigned_to");
  const watchDependencies = watch("dependency_ids");

  const handleClose = useCallback(() => {
    reset();
    onOpenChange(false);
  }, [reset, onOpenChange]);

  const onSubmit = async (data: TaskFormData) => {
    const payload: TaskCreate = {
      title: data.title,
      description: data.description || undefined,
      instructions: data.instructions || undefined,
      phase: data.phase,
      priority: data.priority,
      assigned_to: data.assigned_to || null,
      due_date: data.due_date || null,
      requires_document: data.requires_document,
      dependency_ids: data.dependency_ids.length > 0 ? data.dependency_ids : undefined,
    };

    try {
      await createTask.mutateAsync(payload);
      handleClose();
    } catch {
      // Error handled by mutation
    }
  };

  const toggleDependency = (taskId: string) => {
    const current = watchDependencies;
    setValue(
      "dependency_ids",
      current.includes(taskId)
        ? current.filter((id) => id !== taskId)
        : [...current, taskId],
    );
  };

  // Only active tasks (non-terminal) can be dependencies
  const availableDependencies = tasks.filter(
    (t) => t.status !== "cancelled",
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Task</DialogTitle>
          <DialogDescription>
            Add a custom task to this matter.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Title */}
          <div>
            <Label htmlFor="title">
              Title <span className="text-danger">*</span>
            </Label>
            <Input
              id="title"
              {...register("title")}
              placeholder="Task title"
              className="mt-1"
            />
            {errors.title && (
              <p className="text-xs text-danger mt-1">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register("description")}
              placeholder="Optional details about this task..."
              rows={3}
              className="mt-1"
            />
          </div>

          {/* Instructions */}
          <div>
            <Label htmlFor="instructions">Instructions</Label>
            <Textarea
              id="instructions"
              {...register("instructions")}
              placeholder="Plain-language instructions for the assignee..."
              rows={2}
              className="mt-1"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Displayed to executors/trustees as guidance.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Phase */}
            <div>
              <Label>Phase</Label>
              <Select
                value={watchPhase}
                onValueChange={(val) => setValue("phase", val as TaskFormData["phase"])}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TASK_PHASE_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Priority */}
            <div>
              <Label>Priority</Label>
              <Select
                value={watchPriority}
                onValueChange={(val) => setValue("priority", val as TaskFormData["priority"])}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TASK_PRIORITY_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Assign to */}
            <div>
              <Label>Assign to</Label>
              <Select
                value={watchAssignedTo || "__none__"}
                onValueChange={(val) => setValue("assigned_to", val === "__none__" ? "" : val)}
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

            {/* Due date */}
            <div>
              <Label htmlFor="due_date">Due date</Label>
              <Input
                id="due_date"
                type="date"
                {...register("due_date")}
                className="mt-1"
              />
            </div>
          </div>

          {/* Requires document */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="requires_document"
              {...register("requires_document")}
              className="size-4 rounded border-border text-primary focus:ring-primary/40"
            />
            <Label htmlFor="requires_document" className="text-sm font-normal">
              Requires a document to complete
            </Label>
          </div>

          {/* Dependencies */}
          {availableDependencies.length > 0 && (
            <div>
              <Label>Dependencies</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Select tasks that must be completed before this one.
              </p>
              <div className="max-h-40 overflow-y-auto rounded-md border border-border p-2 space-y-1">
                {availableDependencies.map((t) => (
                  <label
                    key={t.id}
                    className="flex items-center gap-2 text-sm cursor-pointer hover:bg-surface-elevated rounded px-2 py-1"
                  >
                    <input
                      type="checkbox"
                      checked={watchDependencies.includes(t.id)}
                      onChange={() => toggleDependency(t.id)}
                      className="size-3.5 rounded border-border text-primary focus:ring-primary/40"
                    />
                    <span className="truncate">{t.title}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {createTask.error && (
            <p className="text-sm text-danger">
              Failed to create task. Please try again.
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createTask.isPending}>
              {createTask.isPending && <Loader2 className="size-4 mr-1 animate-spin" />}
              Create Task
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
