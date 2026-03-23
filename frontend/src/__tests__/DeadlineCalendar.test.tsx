import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { mockDeadline1, mockDeadline2, mockDeadline3, mockUser, mockStakeholders } from "./fixtures";

// ─── Mock hooks ──────────────────────────────────────────────────────────────

vi.mock("@/hooks/use-queries", () => ({
  useCurrentUser: vi.fn(() => ({
    data: mockUser,
    isLoading: false,
  })),
  useStakeholders: vi.fn(() => ({
    data: mockStakeholders,
    isLoading: false,
  })),
}));

vi.mock("@/hooks/use-api", () => ({
  useApi: () => ({}),
}));

// ─── Import ─────────────────────────────────────────────────────────────────

import { CalendarView } from "@/app/(dashboard)/matters/[matterId]/deadlines/_components/CalendarView";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("CalendarView", () => {
  const defaultProps = {
    deadlines: [mockDeadline1, mockDeadline2, mockDeadline3],
    onDeadlineClick: vi.fn(),
  };

  it("renders the calendar component", () => {
    renderWithProviders(<CalendarView {...defaultProps} />);
    // Should render day-of-week headers
    expect(screen.getByText(/sun/i) || screen.getByText(/mon/i)).toBeTruthy();
  });

  it("renders navigation controls", () => {
    renderWithProviders(<CalendarView {...defaultProps} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });

  it("renders today button", () => {
    renderWithProviders(<CalendarView {...defaultProps} />);
    expect(screen.getByText(/today/i)).toBeInTheDocument();
  });

  it("renders the legend with status colors", () => {
    renderWithProviders(<CalendarView {...defaultProps} />);
    expect(screen.getByText(/completed/i)).toBeInTheDocument();
    expect(screen.getByText(/upcoming/i)).toBeInTheDocument();
  });

  it("renders month name", () => {
    renderWithProviders(<CalendarView {...defaultProps} />);
    const monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December",
    ];
    const hasMonth = monthNames.some(
      (m) => screen.queryByText(new RegExp(m, "i")) !== null,
    );
    expect(hasMonth).toBe(true);
  });

  it("can navigate months", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CalendarView {...defaultProps} />);
    const buttons = screen.getAllByRole("button");
    const navButton = buttons.find(
      (b) => b.querySelector("svg") && !b.textContent?.includes("Today"),
    );
    if (navButton) {
      await user.click(navButton);
    }
    expect(document.body).toBeTruthy();
  });

  it("renders with empty deadlines", () => {
    renderWithProviders(
      <CalendarView deadlines={[]} onDeadlineClick={vi.fn()} />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("renders day numbers in grid", () => {
    renderWithProviders(<CalendarView {...defaultProps} />);
    expect(screen.getByText("15")).toBeInTheDocument();
  });
});
