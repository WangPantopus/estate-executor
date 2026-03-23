import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "./test-utils";
import {
  mockDashboard,
  mockTaskSummary,
  mockAssetSummary,
  mockDeadline1,
  mockDeadline2,
  mockUser,
  mockStakeholders,
} from "./fixtures";

// ─── Mock hooks ──────────────────────────────────────────────────────────────

vi.mock("@/hooks/use-queries", () => ({
  useMatterDashboard: vi.fn(() => ({
    data: mockDashboard,
    isLoading: false,
    error: null,
  })),
  useTasks: vi.fn(() => ({
    data: { data: [], meta: { total: 0 } },
    isLoading: false,
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
    isPending: false,
  })),
  useUpdateMatter: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useCloseMatter: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}));

vi.mock("@/hooks/use-api", () => ({
  useApi: () => ({}),
}));

// ─── Import components under test ───────────────────────────────────────────

import { MetricsRow } from "@/app/(dashboard)/matters/[matterId]/_components/MetricsRow";
import { StatusBadge } from "@/components/layout/StatusBadge";

// ─── MetricsRow tests ───────────────────────────────────────────────────────

describe("MetricsRow", () => {
  const defaultProps = {
    taskSummary: mockTaskSummary,
    assetSummary: mockAssetSummary,
    upcomingDeadlines: [mockDeadline1, mockDeadline2],
  };

  it("renders task completion count", () => {
    renderWithProviders(<MetricsRow {...defaultProps} />);
    // 3 complete + 1 waived = 4 of 10
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText(/\/ 10/)).toBeInTheDocument();
  });

  it("displays task completion percentage", () => {
    renderWithProviders(<MetricsRow {...defaultProps} />);
    expect(screen.getByText("40%")).toBeInTheDocument();
  });

  it("shows overdue count", () => {
    renderWithProviders(<MetricsRow {...defaultProps} />);
    expect(screen.getByText(/2 items/)).toBeInTheDocument();
  });

  it("shows All clear when no overdue", () => {
    renderWithProviders(
      <MetricsRow
        {...defaultProps}
        taskSummary={{ ...mockTaskSummary, overdue: 0 }}
      />,
    );
    expect(screen.getByText(/all clear/i)).toBeInTheDocument();
  });

  it("renders next deadline title", () => {
    renderWithProviders(<MetricsRow {...defaultProps} />);
    expect(screen.getByText("Federal Estate Tax Return")).toBeInTheDocument();
  });

  it("shows None upcoming when no deadlines", () => {
    renderWithProviders(
      <MetricsRow {...defaultProps} upcomingDeadlines={[]} />,
    );
    expect(screen.getByText(/none upcoming/i)).toBeInTheDocument();
  });

  it("displays estate value", () => {
    renderWithProviders(<MetricsRow {...defaultProps} />);
    expect(screen.getByText("$2,500,000")).toBeInTheDocument();
  });

  it("shows dash when no estate value", () => {
    renderWithProviders(
      <MetricsRow
        {...defaultProps}
        assetSummary={{ ...mockAssetSummary, total_estimated_value: 0 }}
      />,
    );
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders section labels", () => {
    renderWithProviders(<MetricsRow {...defaultProps} />);
    expect(screen.getByText("Tasks")).toBeInTheDocument();
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    expect(screen.getByText("Next Deadline")).toBeInTheDocument();
    expect(screen.getByText("Est. Value")).toBeInTheDocument();
  });
});

// ─── StatusBadge tests ──────────────────────────────────────────────────────

describe("StatusBadge", () => {
  it("renders task status labels", () => {
    const { rerender } = renderWithProviders(<StatusBadge status="not_started" />);
    expect(screen.getByText("Not Started")).toBeInTheDocument();

    rerender(<StatusBadge status="in_progress" />);
    expect(screen.getByText("In Progress")).toBeInTheDocument();

    rerender(<StatusBadge status="complete" />);
    expect(screen.getByText("Complete")).toBeInTheDocument();
  });

  it("renders overdue with danger variant", () => {
    renderWithProviders(<StatusBadge status="overdue" />);
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });

  it("renders blocked with warning variant", () => {
    renderWithProviders(<StatusBadge status="blocked" />);
    expect(screen.getByText("Blocked")).toBeInTheDocument();
  });

  it("renders asset statuses", () => {
    const { rerender } = renderWithProviders(<StatusBadge status="discovered" />);
    expect(screen.getByText("Discovered")).toBeInTheDocument();

    rerender(<StatusBadge status="valued" />);
    expect(screen.getByText("Valued")).toBeInTheDocument();

    rerender(<StatusBadge status="distributed" />);
    expect(screen.getByText("Distributed")).toBeInTheDocument();
  });

  it("renders deadline statuses", () => {
    const { rerender } = renderWithProviders(<StatusBadge status="upcoming" />);
    expect(screen.getByText("Upcoming")).toBeInTheDocument();

    rerender(<StatusBadge status="missed" />);
    expect(screen.getByText("Missed")).toBeInTheDocument();
  });

  it("renders matter statuses", () => {
    const { rerender } = renderWithProviders(<StatusBadge status="active" />);
    expect(screen.getByText("Active")).toBeInTheDocument();

    rerender(<StatusBadge status="closed" />);
    expect(screen.getByText("Closed")).toBeInTheDocument();
  });

  it("handles unknown status gracefully", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- intentionally testing unknown status
    renderWithProviders(<StatusBadge status={"unknown" as any} />);
    expect(screen.getByText("unknown")).toBeInTheDocument();
  });
});
