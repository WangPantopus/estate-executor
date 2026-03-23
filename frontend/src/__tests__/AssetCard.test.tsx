import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { mockAsset1, mockAsset2 } from "./fixtures";
import type { AssetListItem } from "@/lib/types";

// ─── Mock hooks ──────────────────────────────────────────────────────────────

vi.mock("@/hooks/use-queries", () => ({
  useCurrentUser: vi.fn(() => ({
    data: { user_id: "user-1", email: "admin@example.com" },
    isLoading: false,
  })),
  useStakeholders: vi.fn(() => ({
    data: { data: [{ email: "admin@example.com", role: "matter_admin" }] },
    isLoading: false,
  })),
}));

vi.mock("@/hooks/use-api", () => ({
  useApi: () => ({}),
}));

// ─── Import ─────────────────────────────────────────────────────────────────

import { AssetCard } from "@/app/(dashboard)/matters/[matterId]/assets/_components/AssetCard";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("AssetCard", () => {
  const onClick = vi.fn();
  const user = userEvent.setup();

  it("renders asset title", () => {
    renderWithProviders(<AssetCard asset={mockAsset1} onClick={onClick} />);
    expect(screen.getByText("Primary Residence")).toBeInTheDocument();
  });

  it("renders asset type label", () => {
    renderWithProviders(<AssetCard asset={mockAsset1} onClick={onClick} />);
    expect(screen.getByText("Real estate")).toBeInTheDocument();
  });

  it("displays status badge", () => {
    renderWithProviders(<AssetCard asset={mockAsset1} onClick={onClick} />);
    expect(screen.getByText("Valued")).toBeInTheDocument();
  });

  it("formats currency value correctly", () => {
    renderWithProviders(<AssetCard asset={mockAsset1} onClick={onClick} />);
    expect(screen.getByText("$850,000")).toBeInTheDocument();
  });

  it("shows masked account number", () => {
    renderWithProviders(<AssetCard asset={mockAsset2} onClick={onClick} />);
    expect(screen.getByText("****4567")).toBeInTheDocument();
  });

  it("shows institution name", () => {
    renderWithProviders(<AssetCard asset={mockAsset2} onClick={onClick} />);
    expect(screen.getByText(/Chase Bank/)).toBeInTheDocument();
  });

  it("displays ownership type badge", () => {
    renderWithProviders(<AssetCard asset={mockAsset1} onClick={onClick} />);
    expect(screen.getByText("Individual")).toBeInTheDocument();
  });

  it("displays transfer mechanism badge", () => {
    renderWithProviders(<AssetCard asset={mockAsset1} onClick={onClick} />);
    expect(screen.getByText("Probate")).toBeInTheDocument();
  });

  it("shows linked entity name", () => {
    renderWithProviders(<AssetCard asset={mockAsset1} onClick={onClick} />);
    expect(screen.getByText("Doe Family Trust")).toBeInTheDocument();
  });

  it("shows No linked entity when no entities", () => {
    renderWithProviders(<AssetCard asset={mockAsset2} onClick={onClick} />);
    expect(screen.getByText("No linked entity")).toBeInTheDocument();
  });

  it("shows document count", () => {
    renderWithProviders(<AssetCard asset={mockAsset1} onClick={onClick} />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("calls onClick when card is clicked", async () => {
    renderWithProviders(<AssetCard asset={mockAsset1} onClick={onClick} />);
    const card = screen.getByText("Primary Residence").closest("[class*='cursor-pointer']");
    if (card) await user.click(card);
    expect(onClick).toHaveBeenCalled();
  });

  it("shows No valuation when no value", () => {
    const noValueAsset: AssetListItem = {
      ...mockAsset2,
      current_estimated_value: null,
      date_of_death_value: null,
    };
    renderWithProviders(<AssetCard asset={noValueAsset} onClick={onClick} />);
    expect(screen.getByText("No valuation")).toBeInTheDocument();
  });

  it("falls back to DOD value when current value is null", () => {
    const dodOnlyAsset: AssetListItem = {
      ...mockAsset2,
      current_estimated_value: null,
      date_of_death_value: 42000,
    };
    renderWithProviders(<AssetCard asset={dodOnlyAsset} onClick={onClick} />);
    expect(screen.getByText("$42,000")).toBeInTheDocument();
  });

  it("renders joint tenancy ownership type", () => {
    renderWithProviders(<AssetCard asset={mockAsset2} onClick={onClick} />);
    expect(screen.getByText("Joint Tenancy")).toBeInTheDocument();
  });
});
