/**
 * Tests for the Distribution Ledger types, API client methods, and data shapes.
 */

import { describe, it, expect, vi } from "vitest";
import type {
  DistributionCreate,
  DistributionResponse,
  DistributionSummaryResponse,
  BeneficiarySummaryItem,
  DistributionType,
} from "@/lib/types";

// ─── Mock data ──────────────────────────────────────────────────────────────

const mockDistributions: DistributionResponse[] = [
  {
    id: "dist-1",
    matter_id: "matter-1",
    asset_id: "asset-1",
    asset_title: "Primary Residence",
    beneficiary_stakeholder_id: "stake-1",
    beneficiary_name: "Jane Doe",
    amount: 250000,
    description: "Transfer of primary residence",
    distribution_type: "asset_transfer",
    distribution_date: "2026-03-15",
    receipt_acknowledged: true,
    receipt_acknowledged_at: "2026-03-20T10:00:00Z",
    notes: "Deed transferred",
    created_at: "2026-03-15T10:00:00Z",
  },
  {
    id: "dist-2",
    matter_id: "matter-1",
    asset_id: null,
    asset_title: null,
    beneficiary_stakeholder_id: "stake-2",
    beneficiary_name: "John Doe",
    amount: 50000,
    description: "Cash distribution from estate account",
    distribution_type: "cash",
    distribution_date: "2026-03-16",
    receipt_acknowledged: false,
    receipt_acknowledged_at: null,
    notes: null,
    created_at: "2026-03-16T10:00:00Z",
  },
  {
    id: "dist-3",
    matter_id: "matter-1",
    asset_id: null,
    asset_title: null,
    beneficiary_stakeholder_id: "stake-1",
    beneficiary_name: "Jane Doe",
    amount: null,
    description: "Family heirloom jewelry",
    distribution_type: "in_kind",
    distribution_date: "2026-03-17",
    receipt_acknowledged: false,
    receipt_acknowledged_at: null,
    notes: "Grandmother's ring and necklace",
    created_at: "2026-03-17T10:00:00Z",
  },
];

const mockSummary: DistributionSummaryResponse = {
  total_distributed: 300000,
  total_distributions: 3,
  total_acknowledged: 1,
  total_pending: 2,
  by_beneficiary: [
    {
      stakeholder_id: "stake-1",
      beneficiary_name: "Jane Doe",
      total_distributed: 250000,
      distribution_count: 2,
      acknowledged_count: 1,
      pending_count: 1,
    },
    {
      stakeholder_id: "stake-2",
      beneficiary_name: "John Doe",
      total_distributed: 50000,
      distribution_count: 1,
      acknowledged_count: 0,
      pending_count: 1,
    },
  ],
  by_type: {
    asset_transfer: 250000,
    cash: 50000,
  },
};

// ─── Mock next/navigation ───────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/matters/matter-1/distributions",
  useParams: () => ({ matterId: "matter-1" }),
  useSearchParams: () => new URLSearchParams(),
}));

// ─── Type tests ─────────────────────────────────────────────────────────────

describe("Distribution Types", () => {
  it("should have correct DistributionResponse shape", () => {
    const dist = mockDistributions[0];
    expect(dist.id).toBe("dist-1");
    expect(dist.beneficiary_name).toBe("Jane Doe");
    expect(dist.distribution_type).toBe("asset_transfer");
    expect(dist.receipt_acknowledged).toBe(true);
  });

  it("should allow null amount for in-kind distributions", () => {
    const inKind = mockDistributions[2];
    expect(inKind.amount).toBeNull();
    expect(inKind.distribution_type).toBe("in_kind");
  });

  it("should allow null asset_id for cash distributions", () => {
    const cash = mockDistributions[1];
    expect(cash.asset_id).toBeNull();
    expect(cash.asset_title).toBeNull();
  });
});

describe("Distribution Summary", () => {
  it("should have correct totals", () => {
    expect(mockSummary.total_distributed).toBe(300000);
    expect(mockSummary.total_distributions).toBe(3);
    expect(mockSummary.total_acknowledged).toBe(1);
    expect(mockSummary.total_pending).toBe(2);
  });

  it("should break down by beneficiary", () => {
    expect(mockSummary.by_beneficiary).toHaveLength(2);
    const jane = mockSummary.by_beneficiary[0];
    expect(jane.beneficiary_name).toBe("Jane Doe");
    expect(jane.total_distributed).toBe(250000);
    expect(jane.distribution_count).toBe(2);
  });

  it("should break down by type", () => {
    expect(mockSummary.by_type.asset_transfer).toBe(250000);
    expect(mockSummary.by_type.cash).toBe(50000);
  });

  it("should have consistent totals", () => {
    const beneTotal = mockSummary.by_beneficiary.reduce(
      (sum, b) => sum + b.total_distributed,
      0,
    );
    expect(beneTotal).toBe(mockSummary.total_distributed);
  });
});

describe("Distribution Create", () => {
  it("should create a valid cash distribution", () => {
    const create: DistributionCreate = {
      beneficiary_stakeholder_id: "stake-1",
      amount: 75000,
      description: "Quarterly cash distribution",
      distribution_type: "cash",
      distribution_date: "2026-06-01",
    };
    expect(create.distribution_type).toBe("cash");
    expect(create.asset_id).toBeUndefined();
  });

  it("should create a valid asset transfer distribution", () => {
    const create: DistributionCreate = {
      beneficiary_stakeholder_id: "stake-2",
      asset_id: "asset-5",
      amount: 500000,
      description: "Transfer of brokerage account",
      distribution_type: "asset_transfer",
      distribution_date: "2026-07-01",
      notes: "Full account transfer",
    };
    expect(create.asset_id).toBe("asset-5");
    expect(create.notes).toBe("Full account transfer");
  });

  it("should allow in-kind distribution without amount", () => {
    const create: DistributionCreate = {
      beneficiary_stakeholder_id: "stake-1",
      description: "Personal effects",
      distribution_type: "in_kind",
      distribution_date: "2026-08-01",
    };
    expect(create.amount).toBeUndefined();
  });
});

describe("Distribution API Client Methods", () => {
  it("should have distribution methods on ApiClient", async () => {
    const { ApiClient } = await import("@/lib/api-client");
    const client = new ApiClient({ baseUrl: "http://test" });

    expect(typeof client.getDistributions).toBe("function");
    expect(typeof client.recordDistribution).toBe("function");
    expect(typeof client.acknowledgeDistribution).toBe("function");
    expect(typeof client.getDistributionSummary).toBe("function");
  });
});

describe("Distribution Acknowledgment Flow", () => {
  it("should track acknowledged vs pending", () => {
    const acknowledged = mockDistributions.filter((d) => d.receipt_acknowledged);
    const pending = mockDistributions.filter((d) => !d.receipt_acknowledged);

    expect(acknowledged).toHaveLength(1);
    expect(pending).toHaveLength(2);
  });

  it("should have timestamp for acknowledged distributions", () => {
    const acked = mockDistributions.find((d) => d.receipt_acknowledged);
    expect(acked?.receipt_acknowledged_at).toBeTruthy();
  });

  it("should have null timestamp for pending distributions", () => {
    const pending = mockDistributions.find((d) => !d.receipt_acknowledged);
    expect(pending?.receipt_acknowledged_at).toBeNull();
  });
});
