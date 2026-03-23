"use client";

import { useState } from "react";
import {
  X,
  Calendar,
  UserCircle,
  Paperclip,
  Link2,
  Upload,
  CheckCircle2,
  Ban,
  AlertCircle,
  MessageSquare,
  History,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { StatusBadge } from "@/components/layout/StatusBadge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TASK_PHASE_LABELS } from "@/lib/constants";
import { useTask, useEvents, useUpdateTask, useAssignTask } from "@/hooks";
import type { Task, TaskDetail, Stakeholder, EventResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isOverdue(task: Task): boolean {
  if (!task.due_date) return false;
  if (task.status === "complete" || task.status === "waived" || task.status === "cancelled") return false;
  return new Date(task.due_date) < new Date(new Date().toDateString());
}

function isTerminal(task: Task): boolean {
  return task.status === "complete" || task.status === "waived" || task.status === "cancelled";
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function getStakeholderName(id: string | null, stakeholders: Stakeholder[]): string {
  if (!id) return "Unassigned";
  return stakeholders.find((s) => s.id === id)?.full_name ?? "Unknown";
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface TaskDetailPanelProps {
  taskId: string;
  firmId: string;
  matterId: string;
  tasks: Task[];
  stakeholders: Stakeholder[];
  onClose: () => void;
  onComplete: (taskId: string) => void;
  onWaive: (taskId: string) => void;
  onDelete: (taskId: string) => void;
}

// ─── Panel ────────────────────────────────────────────────────────────────────

export function TaskDetailPanel({
  taskId,
  firmId,
  matterId,
  tasks,
  stakeholders,
  onClose,
  onComplete,
  onWaive,
  onDelete,
}: TaskDetailPanelProps) {
  const { data: taskDetail, isLoading } = useTask(firmId, matterId, taskId);
  const { data: eventsData } = useEvents(firmId, matterId, {
    entity_type: "task",
    per_page: 20,
  });
  const updateTask = useUpdateTask(firmId, matterId);
  const assignTask = useAssignTask(firmId, matterId);

  const [editingDueDate, setEditingDueDate] = useState(false);
  const [dueDateValue, setDueDateValue] = useState("");

  // Use detailed task if loaded, otherwise fall back to list item
  const task: Task | TaskDetail | undefined = taskDetail ?? tasks.find((t) => t.id === taskId);

  if (isLoading && !task) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="h-5 w-40 bg-surface-elevated rounded animate-pulse" />
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>
        <div className="p-4 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-surface-elevated rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Task not found.</p>
      </div>
    );
  }

  const overdue = isOverdue(task);
  const terminal = isTerminal(task);

  // Filter events for this task
  const taskEvents = (eventsData?.data ?? []).filter(
    (e: EventResponse) => e.entity_id === taskId,
  );

  // Find dependency and dependent tasks
  const dependencyTasks = tasks.filter((t) => task.dependencies.includes(t.id));
  const dependentTasks = taskDetail?.dependents
    ? tasks.filter((t) => taskDetail.dependents.includes(t.id))
    : [];

  const handleAssign = (stakeholderId: string) => {
    assignTask.mutate({ taskId: task.id, stakeholderId });
  };

  const handleDueDateSave = () => {
    updateTask.mutate({ taskId: task.id, data: { due_date: dueDateValue || null } });
    setEditingDueDate(false);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={overdue ? "overdue" : task.status} />
            {task.priority === "critical" && <Badge variant="danger">Critical</Badge>}
            {task.priority === "informational" && <Badge variant="info">Info</Badge>}
          </div>
          <h2 className="text-lg font-medium text-foreground">{task.title}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {TASK_PHASE_LABELS[task.phase] ?? task.phase}
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
          <X className="size-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-5">
          {/* Description */}
          {task.description && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-1">Description</h3>
              <p className="text-sm text-foreground whitespace-pre-wrap">{task.description}</p>
            </div>
          )}

          {/* Instructions */}
          {task.instructions && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-1">Instructions</h3>
              <div className="text-sm text-foreground bg-surface-elevated rounded-md p-3 whitespace-pre-wrap">
                {task.instructions}
              </div>
            </div>
          )}

          <Separator />

          {/* Assignment */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <UserCircle className="size-3.5 inline mr-1" />
              Assigned to
            </h3>
            <Select
              value={task.assigned_to ?? "__none__"}
              onValueChange={(val) => {
                if (val !== "__none__") handleAssign(val);
              }}
            >
              <SelectTrigger className="h-9">
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
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <Calendar className="size-3.5 inline mr-1" />
              Due date
            </h3>
            {editingDueDate ? (
              <div className="flex items-center gap-2">
                <Input
                  type="date"
                  value={dueDateValue}
                  onChange={(e) => setDueDateValue(e.target.value)}
                  className="flex-1"
                />
                <Button size="sm" onClick={handleDueDateSave}>
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditingDueDate(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setDueDateValue(task.due_date ?? "");
                  setEditingDueDate(true);
                }}
                className={cn(
                  "text-sm hover:underline",
                  overdue ? "text-danger font-medium" : task.due_date ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {task.due_date ? formatDate(task.due_date) : "No due date — click to set"}
              </button>
            )}
          </div>

          <Separator />

          {/* Dependencies */}
          {(dependencyTasks.length > 0 || dependentTasks.length > 0) && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-2">
                <Link2 className="size-3.5 inline mr-1" />
                Dependencies
              </h3>

              {dependencyTasks.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs text-muted-foreground mb-1">Blocked by:</p>
                  <div className="space-y-1">
                    {dependencyTasks.map((dep) => (
                      <div key={dep.id} className="flex items-center gap-2 text-sm">
                        {dep.status === "complete" || dep.status === "waived" ? (
                          <CheckCircle2 className="size-3.5 text-success" />
                        ) : (
                          <AlertCircle className="size-3.5 text-warning" />
                        )}
                        <span className={cn(isTerminal(dep) && "line-through text-muted-foreground")}>
                          {dep.title}
                        </span>
                        <StatusBadge status={dep.status} className="text-[10px]" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {dependentTasks.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Blocks:</p>
                  <div className="space-y-1">
                    {dependentTasks.map((dep) => (
                      <div key={dep.id} className="flex items-center gap-2 text-sm">
                        <span>{dep.title}</span>
                        <StatusBadge status={dep.status} className="text-[10px]" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Documents */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <Paperclip className="size-3.5 inline mr-1" />
              Documents
              {task.requires_document && (
                <span className="text-danger ml-1">(required)</span>
              )}
            </h3>
            {task.documents.length > 0 ? (
              <div className="space-y-1">
                {task.documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-2 text-sm text-foreground rounded-md bg-surface-elevated px-3 py-2"
                  >
                    <Paperclip className="size-3.5 text-muted-foreground" />
                    <span className="truncate">{doc.filename}</span>
                    {doc.doc_type && (
                      <Badge variant="muted" className="text-[10px] ml-auto">
                        {doc.doc_type}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No documents linked.</p>
            )}
            <div className="flex gap-2 mt-2">
              <Button variant="outline" size="sm" disabled>
                <Upload className="size-3.5 mr-1" />
                Upload
              </Button>
              <Button variant="outline" size="sm" disabled>
                <Link2 className="size-3.5 mr-1" />
                Link existing
              </Button>
            </div>
          </div>

          <Separator />

          {/* Comments */}
          {taskDetail?.comments && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-2">
                <MessageSquare className="size-3.5 inline mr-1" />
                Comments ({taskDetail.comments.length})
              </h3>
              {taskDetail.comments.length > 0 ? (
                <div className="space-y-3">
                  {taskDetail.comments.map((comment) => (
                    <div key={comment.id} className="text-sm">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-medium text-foreground">
                          {getStakeholderName(comment.author_id, stakeholders)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(comment.created_at)}
                        </span>
                      </div>
                      <p className="text-foreground whitespace-pre-wrap">{comment.body}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No comments yet.</p>
              )}
            </div>
          )}

          {/* Activity log */}
          {taskEvents.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-2">
                <History className="size-3.5 inline mr-1" />
                Activity
              </h3>
              <div className="space-y-2">
                {taskEvents.slice(0, 10).map((event: EventResponse) => (
                  <div key={event.id} className="flex items-start gap-2 text-xs">
                    <span className="text-muted-foreground shrink-0">
                      {formatDateTime(event.created_at)}
                    </span>
                    <span className="text-foreground">
                      {event.actor_name ?? event.actor_type} {event.action}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Actions footer */}
      {!terminal && (
        <div className="border-t border-border p-4 flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => onComplete(task.id)}
            className="flex-1"
          >
            <CheckCircle2 className="size-4 mr-1" />
            Complete
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onWaive(task.id)}
          >
            <Ban className="size-4 mr-1" />
            Waive
          </Button>
          {!task.template_key && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => onDelete(task.id)}
            >
              Delete
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
