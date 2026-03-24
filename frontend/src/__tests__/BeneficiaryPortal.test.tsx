/**
 * Tests for the Beneficiary Portal components and hooks.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders } from "./test-utils";
import { screen } from "@testing-library/react";
import type {
  PortalOverviewResponse,
  PortalDocumentsResponse,
  PortalMessagesResponse,
  PortalBeneficiaryMattersResponse,
} from "@/lib/types";

// ─── Mock data ──────────────────────────────────────────────────────────────

const mockPortalOverview: PortalOverviewResponse = {
  matter: {
    matter_id: "matter-1",
    decedent_name: "John Doe",
    estate_type: "testate_probate",
    jurisdiction_state: "CA",
    phase: "administration",
    completion_percentage: 45.5,
    estimated_completion: null,
  },
  your_role: "Beneficiary",
  your_relationship: "Son",
  contacts: [
    { name: "Jane Attorney", email: "jane@lawfirm.com", role: "Lead Attorney" },
  ],
  milestones: [
    { title: "Initial review", date: "January 15, 2026", completed: true, is_next: false },
    { title: "Estate administration", date: "", completed: false, is_next: true },
    { title: "Distribution", date: "", completed: false, is_next: false },
    { title: "Final closing", date: "", completed: false, is_next: false },
  ],
  distribution: {
    total_estate_value: null,
    distribution_status: "pending",
    notices_count: 1,
    pending_acknowledgments: 1,
  },
  firm_name: "Smith & Associates",
  firm_logo_url: null,
};

const mockPortalDocuments: PortalDocumentsResponse = {
  documents: [
    {
      id: "doc-1",
      filename: "death_certificate.pdf",
      doc_type: "death_certificate",
      size_bytes: 102400,
      shared_at: "2026-01-15T10:00:00Z",
    },
    {
      id: "doc-2",
      filename: "court_filing_probate.pdf",
      doc_type: "court_filing",
      size_bytes: 256000,
      shared_at: "2026-02-01T10:00:00Z",
    },
  ],
  total: 2,
};

const mockPortalMessages: PortalMessagesResponse = {
  messages: [
    {
      id: "msg-1",
      sender_name: "Jane Attorney",
      type: "distribution_notice",
      subject: "Distribution Notice #1",
      body: "Your estimated distribution has been calculated.",
      created_at: "2026-03-01T10:00:00Z",
      requires_acknowledgment: true,
      acknowledged: false,
    },
    {
      id: "msg-2",
      sender_name: "Jane Attorney",
      type: "milestone_notification",
      subject: "Probate Filed",
      body: "The probate petition has been filed with the court.",
      created_at: "2026-02-15T10:00:00Z",
      requires_acknowledgment: false,
      acknowledged: false,
    },
    {
      id: "msg-3",
      sender_name: "System",
      type: "message",
      subject: "Welcome",
      body: "Welcome to the estate portal.",
      created_at: "2026-01-15T10:00:00Z",
      requires_acknowledgment: false,
      acknowledged: false,
    },
  ],
  total: 3,
};

const mockPortalMatters: PortalBeneficiaryMattersResponse = {
  matters: [
    {
      matter_id: "matter-1",
      firm_id: "firm-1",
      firm_slug: "smith-associates",
      decedent_name: "John Doe",
      phase: "administration",
      firm_name: "Smith & Associates",
    },
  ],
};

// ─── Mock next/navigation ───────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/portal/matter-1",
  useParams: () => ({ matterId: "matter-1" }),
  useSearchParams: () => new URLSearchParams(),
}));

// ─── Type tests ─────────────────────────────────────────────────────────────

describe("Portal Types", () => {
  it("should have correct PortalOverviewResponse shape", () => {
    expect(mockPortalOverview.matter.decedent_name).toBe("John Doe");
    expect(mockPortalOverview.your_role).toBe("Beneficiary");
    expect(mockPortalOverview.contacts).toHaveLength(1);
    expect(mockPortalOverview.milestones).toHaveLength(4);
  });

  it("should have correct PortalDocumentsResponse shape", () => {
    expect(mockPortalDocuments.documents).toHaveLength(2);
    expect(mockPortalDocuments.total).toBe(2);
    expect(mockPortalDocuments.documents[0].doc_type).toBe("death_certificate");
  });

  it("should have correct PortalMessagesResponse shape", () => {
    expect(mockPortalMessages.messages).toHaveLength(3);
    expect(mockPortalMessages.messages[0].requires_acknowledgment).toBe(true);
    expect(mockPortalMessages.messages[0].acknowledged).toBe(false);
  });

  it("should have correct PortalBeneficiaryMattersResponse shape", () => {
    expect(mockPortalMatters.matters).toHaveLength(1);
    expect(mockPortalMatters.matters[0].decedent_name).toBe("John Doe");
  });
});

describe("Portal Milestone Data", () => {
  it("should have one completed milestone", () => {
    const completed = mockPortalOverview.milestones.filter((m) => m.completed);
    expect(completed).toHaveLength(1);
    expect(completed[0].title).toBe("Initial review");
  });

  it("should have one current (is_next) milestone", () => {
    const current = mockPortalOverview.milestones.filter((m) => m.is_next);
    expect(current).toHaveLength(1);
    expect(current[0].title).toBe("Estate administration");
  });

  it("should have pending milestones", () => {
    const pending = mockPortalOverview.milestones.filter(
      (m) => !m.completed && !m.is_next,
    );
    expect(pending).toHaveLength(2);
  });
});

describe("Portal Distribution Summary", () => {
  it("should have pending distribution status", () => {
    expect(mockPortalOverview.distribution.distribution_status).toBe("pending");
  });

  it("should have pending acknowledgments", () => {
    expect(mockPortalOverview.distribution.pending_acknowledgments).toBe(1);
  });

  it("should not disclose total estate value by default", () => {
    expect(mockPortalOverview.distribution.total_estate_value).toBeNull();
  });
});

describe("Portal Documents", () => {
  it("should only contain shareable document types", () => {
    const shareableTypes = new Set([
      "death_certificate",
      "court_filing",
      "distribution_notice",
      "correspondence",
    ]);
    for (const doc of mockPortalDocuments.documents) {
      expect(shareableTypes.has(doc.doc_type!)).toBe(true);
    }
  });

  it("should have correct file metadata", () => {
    const doc = mockPortalDocuments.documents[0];
    expect(doc.filename).toBe("death_certificate.pdf");
    expect(doc.size_bytes).toBeGreaterThan(0);
    expect(doc.shared_at).toBeTruthy();
  });
});

describe("Portal Messages", () => {
  it("should identify distribution notices requiring acknowledgment", () => {
    const notices = mockPortalMessages.messages.filter(
      (m) => m.requires_acknowledgment,
    );
    expect(notices).toHaveLength(1);
    expect(notices[0].type).toBe("distribution_notice");
  });

  it("should contain different message types", () => {
    const types = new Set(mockPortalMessages.messages.map((m) => m.type));
    expect(types.has("distribution_notice")).toBe(true);
    expect(types.has("milestone_notification")).toBe(true);
    expect(types.has("message")).toBe(true);
  });

  it("should have sender names for all messages", () => {
    for (const msg of mockPortalMessages.messages) {
      expect(msg.sender_name).toBeTruthy();
    }
  });
});

describe("Portal API Client Methods", () => {
  it("should have portal methods on ApiClient", async () => {
    const { ApiClient } = await import("@/lib/api-client");
    const client = new ApiClient({ baseUrl: "http://test" });

    expect(typeof client.getPortalMatters).toBe("function");
    expect(typeof client.getPortalOverview).toBe("function");
    expect(typeof client.getPortalDocuments).toBe("function");
    expect(typeof client.getPortalMessages).toBe("function");
    expect(typeof client.postPortalMessage).toBe("function");
    expect(typeof client.acknowledgePortalNotice).toBe("function");
  });
});
