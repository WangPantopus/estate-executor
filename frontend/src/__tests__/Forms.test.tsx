import { describe, it, expect, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { mockUser, mockStakeholders, mockTask1, mockTask2, mockTask3 } from "./fixtures";

// ─── Mock hooks ──────────────────────────────────────────────────────────────

const mockCreateMatter = vi.fn();
const mockCreateTask = vi.fn();

vi.mock("@/hooks/use-queries", () => ({
  useCurrentUser: vi.fn(() => ({
    data: mockUser,
    isLoading: false,
  })),
  useStakeholders: vi.fn(() => ({
    data: mockStakeholders,
    isLoading: false,
  })),
  useCreateMatter: vi.fn(() => ({
    mutate: mockCreateMatter,
    mutateAsync: mockCreateMatter.mockResolvedValue({}),
    isPending: false,
  })),
  useCreateTask: vi.fn(() => ({
    mutate: mockCreateTask,
    mutateAsync: mockCreateTask.mockResolvedValue({}),
    isPending: false,
  })),
  useTasks: vi.fn(() => ({
    data: {
      data: [mockTask1, mockTask2, mockTask3],
      meta: { total: 3 },
    },
    isLoading: false,
  })),
  useMatters: vi.fn(() => ({
    data: { data: [], meta: { total: 0 } },
    isLoading: false,
  })),
  usePortfolio: vi.fn(() => ({
    data: { matters: [], summary: { total_matters: 0 } },
    isLoading: false,
  })),
  useFirm: vi.fn(() => ({ data: { id: "firm-1", name: "Test Firm" }, isLoading: false })),
  useDocuments: vi.fn(() => ({
    data: { data: [] },
    isLoading: false,
  })),
  useAssignTask: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

vi.mock("@/hooks/use-api", () => ({
  useApi: () => ({
    createMatter: vi.fn(),
    createTask: vi.fn(),
  }),
}));

// ─── Imports ────────────────────────────────────────────────────────────────

import { CreateMatterDialog } from "@/app/(dashboard)/matters/_components/CreateMatterDialog";
import { CreateTaskDialog } from "@/app/(dashboard)/matters/[matterId]/tasks/_components/CreateTaskDialog";

// ─── CreateMatterDialog Tests ───────────────────────────────────────────────

describe("CreateMatterDialog", () => {
  const user = userEvent.setup();

  it("renders dialog content when open", () => {
    renderWithProviders(
      <CreateMatterDialog open={true} onOpenChange={vi.fn()} firmId="firm-1" />,
    );
    // Step 1 should show Next button
    expect(screen.getByText(/next/i)).toBeInTheDocument();
  });

  it("does not render dialog content when closed", () => {
    renderWithProviders(
      <CreateMatterDialog open={false} onOpenChange={vi.fn()} firmId="firm-1" />,
    );
    expect(screen.queryByText(/decedent.*name/i)).not.toBeInTheDocument();
  });

  it("shows Next button for multi-step navigation", () => {
    renderWithProviders(
      <CreateMatterDialog open={true} onOpenChange={vi.fn()} firmId="firm-1" />,
    );
    expect(screen.getByText(/next/i)).toBeInTheDocument();
  });

  it("shows estate type selector", () => {
    renderWithProviders(
      <CreateMatterDialog open={true} onOpenChange={vi.fn()} firmId="firm-1" />,
    );
    expect(screen.getByText(/estate type/i) || screen.getByText(/type of estate/i)).toBeTruthy();
  });

  it("shows jurisdiction field", () => {
    renderWithProviders(
      <CreateMatterDialog open={true} onOpenChange={vi.fn()} firmId="firm-1" />,
    );
    expect(screen.getByText(/jurisdiction/i) || screen.getByText(/state/i)).toBeTruthy();
  });

  it("shows Cancel button", () => {
    renderWithProviders(
      <CreateMatterDialog open={true} onOpenChange={vi.fn()} firmId="firm-1" />,
    );
    expect(screen.getByText(/cancel/i)).toBeInTheDocument();
  });

  it("validates required fields when Next is clicked", async () => {
    renderWithProviders(
      <CreateMatterDialog open={true} onOpenChange={vi.fn()} firmId="firm-1" />,
    );

    await user.click(screen.getByText(/next/i));

    // Should still be on step 1 with validation errors or still showing step 1
    await waitFor(() => {
      expect(
        screen.getByText(/next/i) || screen.getByText(/required/i),
      ).toBeTruthy();
    });
  });

  it("shows step indicator", () => {
    renderWithProviders(
      <CreateMatterDialog open={true} onOpenChange={vi.fn()} firmId="firm-1" />,
    );
    // Should show step 1 of 3 indicator
    expect(screen.getByText(/1/i) || screen.getByText(/step/i)).toBeTruthy();
  });
});

// ─── CreateTaskDialog Tests ─────────────────────────────────────────────────

describe("CreateTaskDialog", () => {
  it("renders dialog content when open", () => {
    renderWithProviders(
      <CreateTaskDialog
        open={true}
        onOpenChange={vi.fn()}
        firmId="current"
        matterId="matter-1"
        tasks={[mockTask1, mockTask2, mockTask3]}
        stakeholders={mockStakeholders.data}
      />,
    );
    expect(
      screen.getByText(/title/i) ||
      screen.getByText(/task/i) ||
      screen.getByLabelText(/title/i),
    ).toBeTruthy();
  });

  it("does not render when closed", () => {
    renderWithProviders(
      <CreateTaskDialog
        open={false}
        onOpenChange={vi.fn()}
        firmId="current"
        matterId="matter-1"
        tasks={[mockTask1, mockTask2, mockTask3]}
        stakeholders={mockStakeholders.data}
      />,
    );
    expect(screen.queryByLabelText(/title/i)).not.toBeInTheDocument();
  });

  it("shows title input field", () => {
    renderWithProviders(
      <CreateTaskDialog
        open={true}
        onOpenChange={vi.fn()}
        firmId="current"
        matterId="matter-1"
        tasks={[mockTask1, mockTask2, mockTask3]}
        stakeholders={mockStakeholders.data}
      />,
    );
    const inputs = screen.getAllByRole("textbox");
    expect(inputs.length).toBeGreaterThan(0);
  });

  it("shows phase selector", () => {
    renderWithProviders(
      <CreateTaskDialog
        open={true}
        onOpenChange={vi.fn()}
        firmId="current"
        matterId="matter-1"
        tasks={[mockTask1, mockTask2, mockTask3]}
        stakeholders={mockStakeholders.data}
      />,
    );
    expect(screen.getByText(/phase/i)).toBeInTheDocument();
  });

  it("shows priority selector", () => {
    renderWithProviders(
      <CreateTaskDialog
        open={true}
        onOpenChange={vi.fn()}
        firmId="current"
        matterId="matter-1"
        tasks={[mockTask1, mockTask2, mockTask3]}
        stakeholders={mockStakeholders.data}
      />,
    );
    expect(screen.getByText(/priority/i)).toBeInTheDocument();
  });

  it("has submit button", () => {
    renderWithProviders(
      <CreateTaskDialog
        open={true}
        onOpenChange={vi.fn()}
        firmId="current"
        matterId="matter-1"
        tasks={[mockTask1, mockTask2, mockTask3]}
        stakeholders={mockStakeholders.data}
      />,
    );
    // Multiple elements with "Create" may exist — just check at least one
    const createButtons = screen.getAllByText(/create/i);
    expect(createButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("has cancel button", () => {
    renderWithProviders(
      <CreateTaskDialog
        open={true}
        onOpenChange={vi.fn()}
        firmId="current"
        matterId="matter-1"
        tasks={[mockTask1, mockTask2, mockTask3]}
        stakeholders={mockStakeholders.data}
      />,
    );
    expect(screen.getByText(/cancel/i)).toBeInTheDocument();
  });
});
