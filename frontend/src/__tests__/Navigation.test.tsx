import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "./test-utils";

// ─── Mock hooks ──────────────────────────────────────────────────────────────

vi.mock("@/hooks/use-queries", () => ({
  useCurrentUser: vi.fn(() => ({
    data: {
      user_id: "user-1",
      email: "admin@example.com",
      full_name: "Test Admin",
      firm_memberships: [
        { firm_id: "firm-1", firm_name: "Test Law Firm", firm_role: "owner" },
      ],
    },
    isLoading: false,
  })),
  useStakeholders: vi.fn(() => ({
    data: {
      data: [
        { email: "admin@example.com", role: "matter_admin" },
      ],
    },
    isLoading: false,
  })),
}));

vi.mock("@/hooks/use-api", () => ({
  useApi: () => ({}),
}));

// We override usePathname per-describe to control matter context
const mockPathname = vi.fn(() => "/matters");

vi.mock("next/navigation", async () => {
  return {
    useRouter: () => ({
      push: vi.fn(),
      replace: vi.fn(),
      back: vi.fn(),
      prefetch: vi.fn(),
      refresh: vi.fn(),
    }),
    usePathname: () => mockPathname(),
    useParams: () => ({}),
    useSearchParams: () => new URLSearchParams(),
  };
});

// ─── Import ─────────────────────────────────────────────────────────────────

import { AppShell } from "@/components/layout/AppShell";

// ─── Tests: Global navigation (not in matter) ──────────────────────────────

describe("AppShell — global navigation", () => {
  it("renders the app shell with children", () => {
    mockPathname.mockReturnValue("/matters");
    renderWithProviders(
      <AppShell>
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("renders firm name when provided", () => {
    mockPathname.mockReturnValue("/matters");
    renderWithProviders(
      <AppShell firmName="Test Law Firm">
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Test Law Firm")).toBeInTheDocument();
  });

  it("renders Matters nav link", () => {
    mockPathname.mockReturnValue("/matters");
    renderWithProviders(
      <AppShell>
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Matters")).toBeInTheDocument();
  });

  it("renders Settings nav link", () => {
    mockPathname.mockReturnValue("/matters");
    renderWithProviders(
      <AppShell>
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("renders user info when provided", () => {
    mockPathname.mockReturnValue("/matters");
    renderWithProviders(
      <AppShell userName="Test Admin" userEmail="admin@example.com">
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Test Admin")).toBeInTheDocument();
  });
});

// ─── Tests: Matter-scoped navigation ────────────────────────────────────────

describe("AppShell — matter-scoped navigation", () => {
  it("renders matter sub-navigation items", () => {
    mockPathname.mockReturnValue("/matters/matter-1/tasks");
    renderWithProviders(
      <AppShell>
        <div>Tasks page</div>
      </AppShell>,
    );
    expect(screen.getByText("Tasks page")).toBeInTheDocument();
    const links = screen.getAllByRole("link");
    expect(links.length).toBeGreaterThan(0);
  });

  it("renders Overview link in matter context", () => {
    mockPathname.mockReturnValue("/matters/matter-1");
    renderWithProviders(
      <AppShell>
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Overview")).toBeInTheDocument();
  });

  it("renders Tasks link in matter context", () => {
    mockPathname.mockReturnValue("/matters/matter-1/tasks");
    renderWithProviders(
      <AppShell>
        <div>Content</div>
      </AppShell>,
    );
    // May appear in both desktop and mobile nav
    expect(screen.getAllByText("Tasks").length).toBeGreaterThanOrEqual(1);
  });

  it("renders Assets link in matter context", () => {
    mockPathname.mockReturnValue("/matters/matter-1/tasks");
    renderWithProviders(
      <AppShell>
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Assets")).toBeInTheDocument();
  });

  it("renders Documents link in matter context", () => {
    mockPathname.mockReturnValue("/matters/matter-1/tasks");
    renderWithProviders(
      <AppShell>
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Documents")).toBeInTheDocument();
  });

  it("renders Calendar link in matter context", () => {
    mockPathname.mockReturnValue("/matters/matter-1/tasks");
    renderWithProviders(
      <AppShell>
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Calendar")).toBeInTheDocument();
  });

  it("renders Communications link in matter context", () => {
    mockPathname.mockReturnValue("/matters/matter-1/tasks");
    renderWithProviders(
      <AppShell>
        <div>Content</div>
      </AppShell>,
    );
    expect(screen.getByText("Communications")).toBeInTheDocument();
  });
});
