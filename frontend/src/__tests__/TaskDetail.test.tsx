import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "./test-utils";
import { mockTaskDetail, mockTask1, mockTask2, mockTask3, mockTask4, mockUser, mockStakeholders } from "./fixtures";
import type { Stakeholder } from "@/lib/types";

// ─── Mock hooks ──────────────────────────────────────────────────────────────

vi.mock("@/hooks/use-queries", () => ({
  useTask: vi.fn(() => ({
    data: mockTaskDetail,
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
  useUpdateTask: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useAssignTask: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useDocuments: vi.fn(() => ({
    data: { data: [] },
    isLoading: false,
  })),
  useTasks: vi.fn(() => ({
    data: { data: [mockTask2], meta: { total: 1 } },
    isLoading: false,
  })),
  useEvents: vi.fn(() => ({
    data: { data: [], meta: { total: 0 } },
    isLoading: false,
  })),
  useDeadlines: vi.fn(() => ({
    data: { data: [], meta: { total: 0 } },
    isLoading: false,
  })),
  useLinkTaskDocument: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useDeleteTask: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

vi.mock("@/hooks/use-api", () => ({
  useApi: () => ({}),
}));

// ─── Import ─────────────────────────────────────────────────────────────────

import { TaskDetailPanel } from "@/app/(dashboard)/matters/[matterId]/tasks/_components/TaskDetailPanel";

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

const tasks = [mockTask1, mockTask2, mockTask3, mockTask4];

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("TaskDetailPanel", () => {
  const defaultProps = {
    taskId: "task-2",
    firmId: "current",
    matterId: "matter-1",
    tasks,
    stakeholders,
    onClose: vi.fn(),
    onComplete: vi.fn(),
    onWaive: vi.fn(),
    onDelete: vi.fn(),
  };

  it("renders task title", () => {
    renderWithProviders(<TaskDetailPanel {...defaultProps} />);
    expect(screen.getByText("File Probate Petition")).toBeInTheDocument();
  });

  it("renders task description", () => {
    renderWithProviders(<TaskDetailPanel {...defaultProps} />);
    expect(
      screen.getByText("File the initial probate petition with the court"),
    ).toBeInTheDocument();
  });

  it("displays instructions", () => {
    renderWithProviders(<TaskDetailPanel {...defaultProps} />);
    expect(
      screen.getByText(/file with the superior court/i),
    ).toBeInTheDocument();
  });

  it("shows task status", () => {
    renderWithProviders(<TaskDetailPanel {...defaultProps} />);
    // Task is past due date so renders as "Overdue" instead of "In Progress"
    expect(document.body.textContent).toContain("Overdue");
  });

  it("shows phase info", () => {
    renderWithProviders(<TaskDetailPanel {...defaultProps} />);
    // Task phase should appear somewhere
    expect(document.body.textContent).toContain("Probate");
  });

  it("displays dependency information", () => {
    renderWithProviders(<TaskDetailPanel {...defaultProps} />);
    // Should show the blocking task
    expect(screen.getByText(/obtain death certificate/i)).toBeInTheDocument();
  });

  it("renders close button", () => {
    renderWithProviders(<TaskDetailPanel {...defaultProps} />);
    // There should be an X or close button
    const closeButtons = screen.getAllByRole("button");
    expect(closeButtons.length).toBeGreaterThan(0);
  });

  it("renders assignee name", () => {
    renderWithProviders(<TaskDetailPanel {...defaultProps} />);
    expect(screen.getByText("Test Admin")).toBeInTheDocument();
  });
});

describe("TaskDetailPanel — edge cases", () => {
  it("renders with action buttons", () => {
    renderWithProviders(
      <TaskDetailPanel
        taskId="task-2"
        firmId="current"
        matterId="matter-1"
        tasks={tasks}
        stakeholders={stakeholders}
        onClose={vi.fn()}
        onComplete={vi.fn()}
        onWaive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(1);
  });
});
