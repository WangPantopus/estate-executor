/**
 * Type and API client tests for the mobile app.
 */

import { ApiClient } from "../lib/api-client";
import type {
  Matter,
  UserProfile,
  TaskSummary,
  MatterDashboard,
  AppNotification,
  Task,
  CommunicationResponse,
} from "../lib/types";
import { colors, spacing, fontSize } from "../lib/theme";
import { API_BASE_URL, PHASE_LABELS, TASK_STATUS_LABELS } from "../lib/constants";

// ─── Theme ──────────────────────────────────────────────────────────────────

describe("Theme", () => {
  it("should have luxury color palette", () => {
    expect(colors.primary).toBe("#1a1a2e");
    expect(colors.gold).toBe("#c5a44e");
    expect(colors.background).toBe("#fafaf8");
    expect(colors.surface).toBe("#ffffff");
  });

  it("should have spacing scale", () => {
    expect(spacing.xs).toBe(4);
    expect(spacing.sm).toBe(8);
    expect(spacing.lg).toBe(16);
  });

  it("should have font sizes", () => {
    expect(fontSize.xs).toBe(11);
    expect(fontSize.base).toBe(15);
    expect(fontSize["2xl"]).toBe(24);
  });
});

// ─── Constants ──────────────────────────────────────────────────────────────

describe("Constants", () => {
  it("should have API_BASE_URL", () => {
    expect(API_BASE_URL).toBeTruthy();
  });

  it("should have phase labels", () => {
    expect(PHASE_LABELS["immediate"]).toBe("Immediate");
    expect(PHASE_LABELS["distribution"]).toBe("Distribution");
  });

  it("should have task status labels", () => {
    expect(TASK_STATUS_LABELS["not_started"]).toBe("Not Started");
    expect(TASK_STATUS_LABELS["complete"]).toBe("Complete");
  });
});

// ─── Types ──────────────────────────────────────────────────────────────────

describe("Types", () => {
  it("should create valid Matter object", () => {
    const matter: Matter = {
      id: "m1",
      firm_id: "f1",
      title: "Estate of John Doe",
      status: "active",
      estate_type: "testate_probate",
      jurisdiction_state: "CA",
      date_of_death: "2025-12-01",
      decedent_name: "John Doe",
      estimated_value: 2500000,
      phase: "administration",
      created_at: "2025-12-15T10:00:00Z",
      updated_at: "2026-01-10T10:00:00Z",
      closed_at: null,
    };
    expect(matter.decedent_name).toBe("John Doe");
    expect(matter.phase).toBe("administration");
  });

  it("should create valid UserProfile", () => {
    const user: UserProfile = {
      user_id: "u1",
      email: "admin@lawfirm.com",
      full_name: "Jane Admin",
      firm_memberships: [
        { firm_id: "f1", firm_name: "Smith Law", firm_slug: "smith-law", firm_role: "owner" },
      ],
    };
    expect(user.full_name).toBe("Jane Admin");
    expect(user.firm_memberships).toHaveLength(1);
  });

  it("should create valid Task", () => {
    const task: Task = {
      id: "t1",
      matter_id: "m1",
      title: "File probate petition",
      description: "File with county court",
      phase: "probate_filing",
      status: "not_started",
      priority: "critical",
      assigned_to: null,
      due_date: "2026-04-15",
      completed_at: null,
      created_at: "2026-01-15T10:00:00Z",
    };
    expect(task.priority).toBe("critical");
    expect(task.status).toBe("not_started");
  });

  it("should create valid AppNotification", () => {
    const notif: AppNotification = {
      id: "n1",
      title: "Deadline approaching",
      body: "IRS Form 706 due in 5 days",
      type: "deadline",
      matter_id: "m1",
      matter_title: "Estate of John Doe",
      created_at: new Date().toISOString(),
      read: false,
    };
    expect(notif.type).toBe("deadline");
    expect(notif.read).toBe(false);
  });
});

// ─── API Client ─────────────────────────────────────────────────────────────

describe("ApiClient", () => {
  it("should instantiate with config", () => {
    const client = new ApiClient({
      baseUrl: "http://localhost:8000/api/v1",
      getAccessToken: async () => "test-token",
    });
    expect(client).toBeDefined();
  });

  it("should have all required methods", () => {
    const client = new ApiClient({
      baseUrl: "http://test",
      getAccessToken: async () => null,
    });
    expect(typeof client.getMe).toBe("function");
    expect(typeof client.getMatters).toBe("function");
    expect(typeof client.getMatterDashboard).toBe("function");
    expect(typeof client.getTasks).toBe("function");
    expect(typeof client.completeTask).toBe("function");
    expect(typeof client.getCommunications).toBe("function");
    expect(typeof client.createCommunication).toBe("function");
  });
});
