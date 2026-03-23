"use client";

import { useState, useMemo } from "react";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  AlertCircle,
  Clock,
  Ban,
  Paperclip,
  MoreHorizontal,
  UserCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/layout/StatusBadge";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { TASK_PHASE_LABELS, TASK_PHASE_ORDER, TASK_STATUS_LABELS } from "@/lib/constants";
import type { Task, Stakeholder, TaskStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type GroupBy = "phase" | "status" | "assignee" | "none";

interface TaskListViewProps {
  tasks: Task[];
  stakeholders: Stakeholder[];
  groupBy: GroupBy;
  selectedIds: Set<string>;
  onToggleSelect: (taskId: string) => void;
  onSelectAll: (taskIds: string[]) => void;
  onTaskClick: (taskId: string) => void;
  onComplete: (taskId: string) => void;
  onWaive: (taskId: string) => void;
  onAssign: (taskId: string, stakeholderId: string) => void;
  onEdit: (taskId: string) => void;
  onDelete: (taskId: string) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isOverdue(task: Task): boolean {
  if (!task.due_date) return false;
  if (task.status === "complete" || task.status === "waived" || task.status === "cancelled") return false;
  return new Date(task.due_date) < new Date(new Date().toDateString());
}

function isTerminal(task: Task): boolean {
  return task.status === "complete" || task.status === "waived" || task.status === "cancelled";
}

function formatDueDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff === -1) return "Yesterday";
  if (diff > 0 && diff <= 7) return `In ${diff} days`;
  if (diff < 0 && diff >= -7) return `${Math.abs(diff)} days ago`;

  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function getStakeholderName(id: string | null, stakeholders: Stakeholder[]): string {
  if (!id) return "Unassigned";
  return stakeholders.find((s) => s.id === id)?.full_name ?? "Unknown";
}

function getStatusIcon(status: TaskStatus) {
  switch (status) {
    case "complete":
      return <CheckCircle2 className="size-4 text-success" />;
    case "in_progress":
      return <Clock className="size-4 text-info" />;
    case "blocked":
      return <AlertCircle className="size-4 text-warning" />;
    case "waived":
    case "cancelled":
      return <Ban className="size-4 text-muted-foreground" />;
    default:
      return <Circle className="size-4 text-muted-foreground" />;
  }
}

// ─── Group Logic ──────────────────────────────────────────────────────────────

interface TaskGroup {
  key: string;
  label: string;
  tasks: Task[];
}

function groupTasks(tasks: Task[], groupBy: GroupBy, stakeholders: Stakeholder[]): TaskGroup[] {
  if (groupBy === "none") {
    return [{ key: "all", label: "All Tasks", tasks }];
  }

  const groups = new Map<string, Task[]>();

  for (const task of tasks) {
    let key: string;
    switch (groupBy) {
      case "phase":
        key = task.phase;
        break;
      case "status":
        key = task.status;
        break;
      case "assignee":
        key = task.assigned_to ?? "__unassigned__";
        break;
    }
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(task);
  }

  const entries = Array.from(groups.entries());

  // Sort groups by canonical order
  if (groupBy === "phase") {
    entries.sort(
      (a, b) => TASK_PHASE_ORDER.indexOf(a[0]) - TASK_PHASE_ORDER.indexOf(b[0]),
    );
  }

  return entries.map(([key, tasks]) => {
    let label: string;
    switch (groupBy) {
      case "phase":
        label = TASK_PHASE_LABELS[key] ?? key;
        break;
      case "status":
        label = TASK_STATUS_LABELS[key] ?? key;
        break;
      case "assignee":
        label = key === "__unassigned__" ? "Unassigned" : getStakeholderName(key, stakeholders);
        break;
      default:
        label = key;
    }
    return { key, label, tasks };
  });
}

// ─── Task Row ─────────────────────────────────────────────────────────────────

function TaskRow({
  task,
  stakeholders,
  selected,
  onToggleSelect,
  onTaskClick,
  onComplete,
  onWaive,
  onEdit,
  onDelete,
}: {
  task: Task;
  stakeholders: Stakeholder[];
  selected: boolean;
  onToggleSelect: () => void;
  onTaskClick: () => void;
  onComplete: () => void;
  onWaive: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const overdue = isOverdue(task);
  const terminal = isTerminal(task);
  const assigneeName = getStakeholderName(task.assigned_to, stakeholders);

  return (
    <div
      className={cn(
        "group flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors hover:bg-surface-elevated",
        overdue && "border-l-2 border-l-danger",
        terminal && "opacity-60",
      )}
    >
      {/* Checkbox */}
      <input
        type="checkbox"
        checked={selected}
        onChange={onToggleSelect}
        className="size-4 rounded border-border text-primary focus:ring-primary/40 shrink-0"
      />

      {/* Status icon */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          if (!terminal) onComplete();
        }}
        className={cn("shrink-0", terminal && "pointer-events-none")}
        title={terminal ? undefined : "Mark complete"}
      >
        {getStatusIcon(task.status)}
      </button>

      {/* Title */}
      <button
        type="button"
        onClick={onTaskClick}
        className={cn(
          "flex-1 text-left text-sm font-medium text-foreground truncate hover:underline",
          terminal && "line-through text-muted-foreground",
        )}
      >
        {task.title}
      </button>

      {/* Priority indicator */}
      {task.priority === "critical" && (
        <span className="size-2 rounded-full bg-danger shrink-0" title="Critical" />
      )}
      {task.priority === "informational" && (
        <span className="size-2 rounded-full bg-info shrink-0" title="Informational" />
      )}

      {/* Assignee */}
      <span
        className={cn(
          "hidden sm:inline-flex items-center gap-1 text-xs shrink-0 max-w-[120px] truncate",
          task.assigned_to ? "text-foreground" : "text-muted-foreground",
        )}
      >
        <UserCircle className="size-3.5 shrink-0" />
        {assigneeName}
      </span>

      {/* Due date */}
      {task.due_date && (
        <span
          className={cn(
            "hidden sm:inline text-xs shrink-0",
            overdue ? "text-danger font-medium" : "text-muted-foreground",
          )}
        >
          {formatDueDate(task.due_date)}
        </span>
      )}

      {/* Status badge */}
      <div className="hidden md:block shrink-0">
        <StatusBadge status={overdue ? "overdue" : task.status} />
      </div>

      {/* Document indicator */}
      {task.documents.length > 0 && (
        <span className="hidden sm:inline-flex items-center gap-0.5 text-xs text-muted-foreground shrink-0">
          <Paperclip className="size-3" />
          {task.documents.length}
        </span>
      )}

      {/* Overflow menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 opacity-0 group-hover:opacity-100 shrink-0"
          >
            <MoreHorizontal className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={onEdit}>Edit</DropdownMenuItem>
          <DropdownMenuItem onClick={onEdit}>Assign to...</DropdownMenuItem>

          {!terminal && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onComplete}>Complete</DropdownMenuItem>
              <DropdownMenuItem onClick={onWaive}>Waive</DropdownMenuItem>
            </>
          )}

          {/* Only custom tasks (no template_key) can be deleted */}
          {!task.template_key && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={onDelete}
                className="text-danger focus:text-danger"
              >
                Delete
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// ─── Group Section ────────────────────────────────────────────────────────────

function GroupSection({
  group,
  stakeholders,
  selectedIds,
  defaultOpen,
  onToggleSelect,
  onTaskClick,
  onComplete,
  onWaive,
  onAssign,
  onEdit,
  onDelete,
}: {
  group: TaskGroup;
  stakeholders: Stakeholder[];
  selectedIds: Set<string>;
  defaultOpen: boolean;
  onToggleSelect: (taskId: string) => void;
  onTaskClick: (taskId: string) => void;
  onComplete: (taskId: string) => void;
  onWaive: (taskId: string) => void;
  onAssign: (taskId: string, stakeholderId: string) => void;
  onEdit: (taskId: string) => void;
  onDelete: (taskId: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const completedCount = group.tasks.filter((t) => isTerminal(t)).length;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-2 px-3 py-2 text-sm font-medium text-foreground hover:bg-surface-elevated rounded-md transition-colors"
        >
          {isOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
          <span>{group.label}</span>
          <span className="text-xs text-muted-foreground">
            {completedCount}/{group.tasks.length}
          </span>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="ml-2 border-l border-border">
          {group.tasks.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              stakeholders={stakeholders}
              selected={selectedIds.has(task.id)}
              onToggleSelect={() => onToggleSelect(task.id)}
              onTaskClick={() => onTaskClick(task.id)}
              onComplete={() => onComplete(task.id)}
              onWaive={() => onWaive(task.id)}
              onEdit={() => onEdit(task.id)}
              onDelete={() => onDelete(task.id)}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

// ─── Task List View ───────────────────────────────────────────────────────────

export function TaskListView({
  tasks,
  stakeholders,
  groupBy,
  selectedIds,
  onToggleSelect,
  onTaskClick,
  onComplete,
  onWaive,
  onAssign,
  onEdit,
  onDelete,
}: TaskListViewProps) {
  const { activeGroups, completedGroup } = useMemo(() => {
    // Split into active and terminal tasks
    const activeTasks = tasks.filter((t) => !isTerminal(t));
    const completedTasks = tasks.filter((t) => isTerminal(t));

    // Sort active: overdue first, then by sort_order
    activeTasks.sort((a, b) => {
      const aOverdue = isOverdue(a) ? 0 : 1;
      const bOverdue = isOverdue(b) ? 0 : 1;
      if (aOverdue !== bOverdue) return aOverdue - bOverdue;
      return a.sort_order - b.sort_order;
    });

    const activeGroups = groupTasks(activeTasks, groupBy, stakeholders);
    const completedGroup: TaskGroup | null =
      completedTasks.length > 0
        ? { key: "__completed__", label: `Completed / Waived (${completedTasks.length})`, tasks: completedTasks }
        : null;

    return { activeGroups, completedGroup };
  }, [tasks, groupBy, stakeholders]);

  if (tasks.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">No tasks found.</p>
      </div>
    );
  }

  // For flat/no-group mode, render tasks directly
  if (groupBy === "none") {
    const allActive = activeGroups[0]?.tasks ?? [];
    return (
      <div className="space-y-1">
        {allActive.map((task) => (
          <TaskRow
            key={task.id}
            task={task}
            stakeholders={stakeholders}
            selected={selectedIds.has(task.id)}
            onToggleSelect={() => onToggleSelect(task.id)}
            onTaskClick={() => onTaskClick(task.id)}
            onComplete={() => onComplete(task.id)}
            onWaive={() => onWaive(task.id)}
            onEdit={() => onEdit(task.id)}
            onDelete={() => onDelete(task.id)}
          />
        ))}
        {completedGroup && (
          <GroupSection
            group={completedGroup}
            stakeholders={stakeholders}
            selectedIds={selectedIds}
            defaultOpen={false}
            onToggleSelect={onToggleSelect}
            onTaskClick={onTaskClick}
            onComplete={onComplete}
            onWaive={onWaive}
            onAssign={onAssign}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {activeGroups.map((group) => (
        <GroupSection
          key={group.key}
          group={group}
          stakeholders={stakeholders}
          selectedIds={selectedIds}
          defaultOpen={true}
          onToggleSelect={onToggleSelect}
          onTaskClick={onTaskClick}
          onComplete={onComplete}
          onWaive={onWaive}
          onAssign={onAssign}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
      {completedGroup && (
        <GroupSection
          group={completedGroup}
          stakeholders={stakeholders}
          selectedIds={selectedIds}
          defaultOpen={false}
          onToggleSelect={onToggleSelect}
          onTaskClick={onTaskClick}
          onComplete={onComplete}
          onWaive={onWaive}
          onAssign={onAssign}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      )}
    </div>
  );
}
