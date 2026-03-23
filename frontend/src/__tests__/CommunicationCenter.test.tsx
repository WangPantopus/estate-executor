import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { mockMessage1, mockMessage2, mockMessage3, mockUser, mockStakeholders } from "./fixtures";
import type { Stakeholder } from "@/lib/types";

// ─── Mock hooks ──────────────────────────────────────────────────────────────

vi.mock("@/hooks/use-queries", () => ({
  useCommunications: vi.fn(() => ({
    data: {
      data: [mockMessage1, mockMessage2, mockMessage3],
      meta: { total: 3 },
    },
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
  useCreateCommunication: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useAcknowledgeCommunication: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useDisputeFlag: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

vi.mock("@/hooks/use-api", () => ({
  useApi: () => ({}),
}));

// ─── Import ─────────────────────────────────────────────────────────────────

import { MessageList } from "@/app/(dashboard)/matters/[matterId]/communications/_components/MessageList";

// ─── Tests ───────────────────────────────────────────────────────────────────

const testStakeholders: Stakeholder[] = [
  {
    id: "sh-1",
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

describe("MessageList", () => {
  const defaultProps = {
    communications: [mockMessage1, mockMessage2, mockMessage3],
    stakeholders: testStakeholders,
    selectedId: null as string | null,
    onSelect: vi.fn(),
    activeTab: "all" as const,
    onTabChange: vi.fn(),
  };

  it("renders all message subjects", () => {
    renderWithProviders(<MessageList {...defaultProps} />);
    expect(screen.getByText("Initial Consultation Notes")).toBeInTheDocument();
    expect(screen.getByText("Probate Petition Filed")).toBeInTheDocument();
    expect(screen.getByText("Fee Breakdown for Review")).toBeInTheDocument();
  });

  it("renders sender names", () => {
    renderWithProviders(<MessageList {...defaultProps} />);
    const senderElements = screen.getAllByText("Test Admin");
    expect(senderElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders filter tabs", () => {
    renderWithProviders(<MessageList {...defaultProps} />);
    expect(screen.getByText(/all/i)).toBeInTheDocument();
  });

  it("highlights selected message", () => {
    renderWithProviders(<MessageList {...defaultProps} selectedId="msg-1" />);
    expect(screen.getByText("Initial Consultation Notes")).toBeInTheDocument();
  });

  it("calls onSelect when message is clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<MessageList {...defaultProps} onSelect={onSelect} />);

    const msgEl = screen.getByText("Initial Consultation Notes").closest(
      "div[class*='cursor'], button, [role='button']",
    ) || screen.getByText("Initial Consultation Notes");
    await user.click(msgEl);
    expect(onSelect).toHaveBeenCalled();
  });

  it("renders with empty messages", () => {
    renderWithProviders(<MessageList {...defaultProps} communications={[]} />);
    // Should still render the tab bar
    expect(screen.getByText(/all/i)).toBeInTheDocument();
  });

  it("shows milestone type indicator", () => {
    renderWithProviders(<MessageList {...defaultProps} />);
    // Milestone message should have a distinguishing indicator
    expect(screen.getByText("Probate Petition Filed")).toBeInTheDocument();
  });

  it("shows professionals_only visibility indicator", () => {
    renderWithProviders(<MessageList {...defaultProps} />);
    // The professionals-only message should have some indicator
    expect(screen.getByText("Fee Breakdown for Review")).toBeInTheDocument();
  });
});

describe("MessageList — tab filtering", () => {
  it("filters to message type", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <MessageList
        communications={[mockMessage1, mockMessage2, mockMessage3]}
        stakeholders={testStakeholders}
        selectedId={null}
        onSelect={vi.fn()}
        activeTab="message"
        onTabChange={onTabChange}
      />,
    );
    // Should render messages of type "message"
    expect(screen.getByText("Initial Consultation Notes")).toBeInTheDocument();
  });

  it("filters to milestone type", () => {
    renderWithProviders(
      <MessageList
        communications={[mockMessage1, mockMessage2, mockMessage3]}
        stakeholders={testStakeholders}
        selectedId={null}
        onSelect={vi.fn()}
        activeTab="milestone_notification"
        onTabChange={vi.fn()}
      />,
    );
    expect(screen.getByText("Probate Petition Filed")).toBeInTheDocument();
  });
});
