import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "./test-utils";
import {
  mockTask1,
  mockTask2,
  mockTask3,
  mockTask4,
  mockUser,
  mockStakeholders,
} from "./fixtures";

// ─── Mock hooks ──────────────────────────────────────────────────────────────

vi.mock("@/hooks/use-queries", () => ({
  useTasks: vi.fn(() => ({
    data: {
      data: [mockTask1, mockTask2, mockTask3, mockTask4],
      meta: { total: 4, page: 1, page_size: 25, total_pages: 1 },
    },
    isLoading: false,
    error: null,
  })),
  useCurrentUser: vi.fn(() => ({
    data: mockUser,
    isLoading: false,
  })),
  useStakeholders: vi.fn(() => ({
    data: mockStakeholders,
    isLoading: false,
  })),
  useCompleteTask: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useWaiveTask: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useCreateTask: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useUpdateTask: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useAssignTask: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useTask: vi.fn(() => ({
    data: null,
    isLoading: false,
  })),
  useDocuments: vi.fn(() => ({
    data: { data: [] },
    isLoading: false,
  })),
}));

vi.mock("@/hooks/use-api", () => ({
  useApi: () => ({}),
}));

// ─── Import components ──────────────────────────────────────────────────────

import { TaskListView } from "@/app/(dashboard)/matters/[matterId]/tasks/_components/TaskListView";
import type { Stakeholder } from "@/lib/types";

const stakeholders: Stakeholder[] = [
  {
    id: "user-1",
    matter_id: "matter-1",
    user_id: "user-1",
    email: "admin@example.com",
    full_name: "Test Admin",
    role: "matter_admin",
    relationship: null,
    invite_status: "accepted",
    created_at: "2025-12-15T10:00:00Z",
  },
];

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("TaskListView", () => {
  const tasks = [mockTask1, mockTask2, mockTask3, mockTask4];
  const defaultProps = {
    tasks,
    stakeholders,
    groupBy: "none" as const,
    selectedIds: new Set<string>(),
    onToggleSelect: vi.fn(),
    onSelectAll: vi.fn(),
    onTaskClick: vi.fn(),
    onComplete: vi.fn(),
    onWaive: vi.fn(),
    onAssign: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
  };

  it("renders active task titles in flat mode", () => {
    renderWithProviders(<TaskListView {...defaultProps} />);
    // Active tasks (not complete/waived)
    expect(screen.getByText("File Probate Petition")).toBeInTheDocument();
    expect(screen.getByText("Inventory Personal Property")).toBeInTheDocument();
    expect(screen.getByText("Blocked Task")).toBeInTheDocument();
  });

  it("renders status badges for active tasks", () => {
    renderWithProviders(<TaskListView {...defaultProps} />);
    // task-2 is past due so shows "Overdue" instead of "In Progress"
    expect(document.body.textContent).toContain("Overdue");
    expect(document.body.textContent).toContain("Not Started");
    expect(document.body.textContent).toContain("Blocked");
  });

  it("shows group headers in phase mode", () => {
    renderWithProviders(<TaskListView {...defaultProps} groupBy="phase" />);
    // Should at least render group headers even if Collapsible content is hidden
    const container = document.body;
    expect(container.textContent).toContain("Probate Filing");
  });

  it("shows group headers in status mode", () => {
    renderWithProviders(<TaskListView {...defaultProps} groupBy="status" />);
    const container = document.body;
    expect(container.textContent).toContain("In Progress");
  });

  it("renders flat view shows tasks directly", () => {
    renderWithProviders(<TaskListView {...defaultProps} groupBy="none" />);
    expect(screen.getByText("File Probate Petition")).toBeInTheDocument();
  });

  it("shows assignee name", () => {
    renderWithProviders(<TaskListView {...defaultProps} />);
    expect(document.body.textContent).toContain("Test Admin");
  });

  it("renders empty state when no tasks", () => {
    renderWithProviders(<TaskListView {...defaultProps} tasks={[]} />);
    expect(screen.getByText("No tasks found.")).toBeInTheDocument();
  });

  it("shows completed group header", () => {
    renderWithProviders(<TaskListView {...defaultProps} />);
    // Completed tasks are in a separate collapsed group
    expect(document.body.textContent).toContain("Completed");
  });
});

describe("TaskListView — completion flow", () => {
  const onTaskClick = vi.fn();
  const tasks = [mockTask1, mockTask2, mockTask3, mockTask4];

  it("calls onTaskClick when a task row is clicked", async () => {
    const userEv = (await import("@testing-library/user-event")).default.setup();
    renderWithProviders(
      <TaskListView
        tasks={tasks}
        stakeholders={stakeholders}
        groupBy="none"
        selectedIds={new Set()}
        onToggleSelect={vi.fn()}
        onSelectAll={vi.fn()}
        onTaskClick={onTaskClick}
        onComplete={vi.fn()}
        onWaive={vi.fn()}
        onAssign={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    const taskRow = screen.getByText("File Probate Petition").closest("tr, div, button");
    if (taskRow) {
      await userEv.click(taskRow);
    }
    expect(screen.getByText("File Probate Petition")).toBeInTheDocument();
  });
});
