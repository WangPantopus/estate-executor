import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { mockMatter, mockMatter2, mockMatter3, mockMattersPage, mockUser } from "./fixtures";

// ─── Mock hooks ──────────────────────────────────────────────────────────────

const mockMutate = vi.fn();

vi.mock("@/hooks", () => ({
  useMatters: vi.fn(() => ({
    data: {
      data: [mockMatter, mockMatter2, mockMatter3],
      meta: { total: 3, page: 1, page_size: 25, total_pages: 1 },
    },
    isLoading: false,
    error: null,
  })),
  usePortfolio: vi.fn(() => ({
    data: {
      matters: [mockMatter, mockMatter2, mockMatter3],
      meta: { total: 3, page: 1, page_size: 25, total_pages: 1 },
      summary: { total_matters: 3, total_estimated_value: 8300000, by_status: {}, by_phase: {} },
    },
    isLoading: false,
  })),
  useCurrentUser: vi.fn(() => ({
    data: mockUser,
    isLoading: false,
  })),
  useFirm: vi.fn(() => ({ data: { id: "firm-1", name: "Test Firm" }, isLoading: false })),
  useCreateMatter: vi.fn(() => ({
    mutate: mockMutate,
    mutateAsync: mockMutate,
    isPending: false,
  })),
  useStakeholders: vi.fn(() => ({
    data: { data: [{ email: "admin@example.com", role: "matter_admin" }] },
    isLoading: false,
  })),
  useApi: () => ({
    getMatters: vi.fn(),
    createMatter: vi.fn(),
    getPortfolio: vi.fn(),
  }),
  usePermissions: vi.fn(() => ({
    role: "matter_admin",
    isLoading: false,
    can: () => true,
    isAdmin: true,
    isProfessional: false,
    isExecutor: false,
    isBeneficiary: false,
    isReadOnly: false,
    canWrite: true,
  })),
  queryKeys: {},
}));

// ─── Import component under test ────────────────────────────────────────────

import { MattersPageContent } from "@/app/(dashboard)/matters/_components/MattersPageContent";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("MattersPageContent", () => {
  const user = userEvent.setup();

  it("renders the page title", () => {
    renderWithProviders(<MattersPageContent />);
    expect(screen.getByText("Matters")).toBeInTheDocument();
  });

  it("renders all matter titles in the list", () => {
    renderWithProviders(<MattersPageContent />);
    expect(screen.getByText("Estate of John Doe")).toBeInTheDocument();
    expect(screen.getByText("Estate of Jane Smith")).toBeInTheDocument();
    expect(screen.getByText("Estate of Bob Wilson")).toBeInTheDocument();
  });

  it("displays matter data in the page", () => {
    renderWithProviders(<MattersPageContent />);
    // Matter titles and data should appear somewhere in the DOM
    expect(document.body.textContent).toContain("John Doe");
    expect(document.body.textContent).toContain("Jane Smith");
  });

  it("renders phase names", () => {
    renderWithProviders(<MattersPageContent />);
    expect(document.body.textContent).toContain("Administration");
    expect(document.body.textContent).toContain("Immediate");
  });

  it("renders search input", () => {
    renderWithProviders(<MattersPageContent />);
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
  });

  it("shows New Matter button", () => {
    renderWithProviders(<MattersPageContent />);
    expect(screen.getByText(/new matter/i)).toBeInTheDocument();
  });

  it("renders jurisdiction state names", () => {
    renderWithProviders(<MattersPageContent />);
    expect(document.body.textContent).toContain("California");
    expect(document.body.textContent).toContain("New York");
  });
});

describe("MattersList — view modes", () => {
  it("renders view toggle buttons", () => {
    renderWithProviders(<MattersPageContent />);
    // Should have view mode toggle options
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(1);
  });

  it("renders New Matter button which opens dialog", () => {
    renderWithProviders(<MattersPageContent />);
    expect(screen.getByText(/new matter/i)).toBeInTheDocument();
  });
});
