"use client";

import { use, useState, useMemo, useCallback } from "react";
import {
  Plus,
  Filter,
  List,
  LayoutGrid,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
} from "@/components/ui/sheet";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import { EmptyState } from "@/components/layout/EmptyState";
import {
  useTasks,
  useStakeholders,
  useCompleteTask,
  useWaiveTask,
  useUpdateTask,
  useAssignTask,
} from "@/hooks";
import { usePermissions } from "@/hooks/use-permissions";
import type { TaskStatus, TaskPriority } from "@/lib/types";

import {
  TaskFilterPanel,
  type TaskFilterState,
  EMPTY_FILTERS,
  countActiveFilters,
} from "./_components/TaskFilterPanel";
import { TaskListView, type GroupBy } from "./_components/TaskListView";
import { TaskBoardView } from "./_components/TaskBoardView";
import { TaskDetailPanel } from "./_components/TaskDetailPanel";
import { CreateTaskDialog } from "./_components/CreateTaskDialog";
import { WaiveTaskDialog } from "./_components/WaiveTaskDialog";
import { BulkActionsBar } from "./_components/BulkActionsBar";

// ─── Constants ────────────────────────────────────────────────────────────────

const FIRM_ID = "current";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TasksPage({
  params,
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);

  // ─── Permissions ──────────────────────────────────────────────────────────
  const { canWrite, can: _can, isReadOnly: _isReadOnly, isBeneficiary: _isBeneficiary } = usePermissions(matterId);

  // ─── Data fetching ──────────────────────────────────────────────────────────
  const { data: tasksData, isLoading: tasksLoading, error: tasksError } = useTasks(
    FIRM_ID,
    matterId,
    { per_page: 500 },
  );
  const { data: stakeholdersData } = useStakeholders(FIRM_ID, matterId);

  const allTasks = tasksData?.data ?? [];
  const stakeholders = stakeholdersData?.data ?? [];

  // ─── Mutations ──────────────────────────────────────────────────────────────
  const completeTask = useCompleteTask(FIRM_ID, matterId);
  const waiveTask = useWaiveTask(FIRM_ID, matterId);
  const updateTask = useUpdateTask(FIRM_ID, matterId);
  const assignTask = useAssignTask(FIRM_ID, matterId);

  // ─── UI state ───────────────────────────────────────────────────────────────
  const [viewMode, setViewMode] = useState<"list" | "board">("list");
  const [groupBy, setGroupBy] = useState<GroupBy>("phase");
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<TaskFilterState>(EMPTY_FILTERS);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [detailTaskId, setDetailTaskId] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [waiveTarget, setWaiveTarget] = useState<{ id: string; title: string } | null>(null);

  // ─── Filter logic ───────────────────────────────────────────────────────────
  const filteredTasks = useMemo(() => {
    let result = allTasks;

    if (filters.phases.length > 0) {
      result = result.filter((t) => filters.phases.includes(t.phase));
    }
    if (filters.statuses.length > 0) {
      result = result.filter((t) => filters.statuses.includes(t.status));
    }
    if (filters.priorities.length > 0) {
      result = result.filter((t) => filters.priorities.includes(t.priority));
    }
    if (filters.assignedTo) {
      if (filters.assignedTo === "__unassigned__") {
        result = result.filter((t) => !t.assigned_to);
      } else {
        result = result.filter((t) => t.assigned_to === filters.assignedTo);
      }
    }
    if (filters.dueDateFrom) {
      result = result.filter(
        (t) => t.due_date && t.due_date >= filters.dueDateFrom,
      );
    }
    if (filters.dueDateTo) {
      result = result.filter(
        (t) => t.due_date && t.due_date <= filters.dueDateTo,
      );
    }
    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          (t.description && t.description.toLowerCase().includes(q)),
      );
    }

    return result;
  }, [allTasks, filters]);

  const activeFilterCount = countActiveFilters(filters);

  // ─── Selection ──────────────────────────────────────────────────────────────
  const toggleSelect = useCallback((taskId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  }, []);

  const selectAll = useCallback((taskIds: string[]) => {
    setSelectedIds(new Set(taskIds));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // ─── Task actions ───────────────────────────────────────────────────────────
  const handleComplete = useCallback(
    (taskId: string) => {
      const task = allTasks.find((t) => t.id === taskId);
      if (!task) return;

      // Check dependencies
      const unmetDeps = task.dependencies.filter((depId) => {
        const dep = allTasks.find((t) => t.id === depId);
        return dep && dep.status !== "complete" && dep.status !== "waived";
      });

      if (unmetDeps.length > 0) {
        const depNames = unmetDeps
          .map((id) => allTasks.find((t) => t.id === id)?.title ?? id)
          .join(", ");
        alert(
          `Cannot complete this task. The following blocking tasks are not yet complete:\n\n${depNames}`,
        );
        return;
      }

      // Check document requirement
      if (task.requires_document && task.documents.length === 0) {
        alert(
          "Cannot complete this task. At least one document must be linked because this task requires a document.",
        );
        return;
      }

      completeTask.mutate({ taskId });
    },
    [allTasks, completeTask],
  );

  const handleWaive = useCallback(
    (taskId: string) => {
      const task = allTasks.find((t) => t.id === taskId);
      if (task) {
        setWaiveTarget({ id: taskId, title: task.title });
      }
    },
    [allTasks],
  );

  const handleWaiveConfirm = useCallback(
    (reason: string) => {
      if (waiveTarget) {
        waiveTask.mutate(
          { taskId: waiveTarget.id, reason },
          { onSuccess: () => setWaiveTarget(null) },
        );
      }
    },
    [waiveTarget, waiveTask],
  );

  const handleAssign = useCallback(
    (taskId: string, stakeholderId: string) => {
      assignTask.mutate({ taskId, stakeholderId });
    },
    [assignTask],
  );

  const handleStatusChange = useCallback(
    (taskId: string, newStatus: TaskStatus) => {
      if (newStatus === "complete") {
        handleComplete(taskId);
      } else {
        updateTask.mutate({ taskId, data: { status: newStatus } });
      }
    },
    [handleComplete, updateTask],
  );

  const handleEdit = useCallback(
    (taskId: string) => {
      setDetailTaskId(taskId);
    },
    [],
  );

  const handleDelete = useCallback(
    (taskId: string) => {
      if (confirm("Delete this task? This action cannot be undone.")) {
        // Use update to cancel (API doesn't have delete for tasks, use status cancelled)
        updateTask.mutate({ taskId, data: { status: "cancelled" } });
      }
    },
    [updateTask],
  );

  // ─── Bulk actions ───────────────────────────────────────────────────────────
  const handleBulkAssign = useCallback(
    (stakeholderId: string) => {
      for (const taskId of selectedIds) {
        assignTask.mutate({ taskId, stakeholderId });
      }
      clearSelection();
    },
    [selectedIds, assignTask, clearSelection],
  );

  const handleBulkStatusChange = useCallback(
    (status: TaskStatus) => {
      for (const taskId of selectedIds) {
        if (status === "complete") {
          handleComplete(taskId);
        } else {
          updateTask.mutate({ taskId, data: { status } });
        }
      }
      clearSelection();
    },
    [selectedIds, handleComplete, updateTask, clearSelection],
  );

  const handleBulkPriorityChange = useCallback(
    (priority: TaskPriority) => {
      for (const taskId of selectedIds) {
        updateTask.mutate({ taskId, data: { priority } });
      }
      clearSelection();
    },
    [selectedIds, updateTask, clearSelection],
  );

  // ─── Render ─────────────────────────────────────────────────────────────────
  if (tasksLoading) {
    return <LoadingState variant="list" />;
  }

  if (tasksError) {
    return (
      <div className="py-12 text-center">
        <p className="text-danger">Failed to load tasks.</p>
        <p className="text-sm text-muted-foreground mt-1">Please try refreshing the page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <PageHeader
        title="Tasks"
        actions={
          <div className="flex items-center gap-2">
            {/* Filter toggle */}
            <Button
              variant={showFilters ? "outline" : "ghost"}
              size="sm"
              onClick={() => setShowFilters((v) => !v)}
              className="relative"
            >
              <Filter className="size-4 mr-1" />
              Filters
              {activeFilterCount > 0 && (
                <Badge variant="default" className="ml-1.5 size-5 p-0 flex items-center justify-center text-[10px]">
                  {activeFilterCount}
                </Badge>
              )}
            </Button>

            {/* Group by (list mode only) */}
            {viewMode === "list" && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm">
                    Group
                    <ChevronDown className="size-3.5 ml-1" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>Group by</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => setGroupBy("phase")}>
                    Phase {groupBy === "phase" && "•"}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setGroupBy("status")}>
                    Status {groupBy === "status" && "•"}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setGroupBy("assignee")}>
                    Assignee {groupBy === "assignee" && "•"}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setGroupBy("none")}>
                    Flat list {groupBy === "none" && "•"}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            {/* View toggle */}
            <div className="hidden md:flex items-center rounded-md border border-border">
              <Button
                variant={viewMode === "list" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("list")}
                className="rounded-r-none border-0"
              >
                <List className="size-4" />
              </Button>
              <Button
                variant={viewMode === "board" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("board")}
                className="rounded-l-none border-0"
              >
                <LayoutGrid className="size-4" />
              </Button>
            </div>

            {/* Add task — only for admins/professionals */}
            {canWrite && (
              <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
                <Plus className="size-4 mr-1" />
                Add Task
              </Button>
            )}
          </div>
        }
      />

      {/* Filter panel */}
      {showFilters && (
        <TaskFilterPanel
          filters={filters}
          onChange={setFilters}
          stakeholders={stakeholders}
        />
      )}

      {/* Bulk actions bar */}
      <BulkActionsBar
        selectedCount={selectedIds.size}
        stakeholders={stakeholders}
        onClear={clearSelection}
        onBulkAssign={handleBulkAssign}
        onBulkStatusChange={handleBulkStatusChange}
        onBulkPriorityChange={handleBulkPriorityChange}
      />

      {/* Task count */}
      <p className="text-xs text-muted-foreground">
        {filteredTasks.length} task{filteredTasks.length !== 1 ? "s" : ""}
        {activeFilterCount > 0 && ` (filtered from ${allTasks.length})`}
      </p>

      {/* Content */}
      {filteredTasks.length === 0 && allTasks.length > 0 ? (
        <EmptyState
          title="No tasks match filters"
          description="Try adjusting your filters to see more tasks."
          action={
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setFilters(EMPTY_FILTERS);
                setShowFilters(false);
              }}
            >
              Clear filters
            </Button>
          }
        />
      ) : filteredTasks.length === 0 ? (
        <EmptyState
          title="No tasks yet"
          description="Create a task or generate tasks from the matter template."
          action={
            <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
              <Plus className="size-4 mr-1" />
              Add Task
            </Button>
          }
        />
      ) : viewMode === "list" ? (
        <TaskListView
          tasks={filteredTasks}
          stakeholders={stakeholders}
          groupBy={groupBy}
          selectedIds={selectedIds}
          onToggleSelect={toggleSelect}
          onSelectAll={selectAll}
          onTaskClick={(id) => setDetailTaskId(id)}
          onComplete={handleComplete}
          onWaive={handleWaive}
          onAssign={handleAssign}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      ) : (
        <TaskBoardView
          tasks={filteredTasks}
          stakeholders={stakeholders}
          onTaskClick={(id) => setDetailTaskId(id)}
          onStatusChange={handleStatusChange}
        />
      )}

      {/* Task detail side panel */}
      <Sheet
        open={!!detailTaskId}
        onOpenChange={(open) => {
          if (!open) setDetailTaskId(null);
        }}
      >
        <SheetContent side="right" className="w-full sm:max-w-lg p-0">
          {detailTaskId && (
            <TaskDetailPanel
              taskId={detailTaskId}
              firmId={FIRM_ID}
              matterId={matterId}
              tasks={allTasks}
              stakeholders={stakeholders}
              onClose={() => setDetailTaskId(null)}
              onComplete={handleComplete}
              onWaive={handleWaive}
              onDelete={handleDelete}
            />
          )}
        </SheetContent>
      </Sheet>

      {/* Create task dialog */}
      <CreateTaskDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        firmId={FIRM_ID}
        matterId={matterId}
        tasks={allTasks}
        stakeholders={stakeholders}
      />

      {/* Waive task dialog */}
      <WaiveTaskDialog
        open={!!waiveTarget}
        onOpenChange={(open) => {
          if (!open) setWaiveTarget(null);
        }}
        taskTitle={waiveTarget?.title ?? ""}
        isPending={waiveTask.isPending}
        onConfirm={handleWaiveConfirm}
      />
    </div>
  );
}
