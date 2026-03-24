/**
 * Tests for mobile matter & task screens — data shapes, constants, API methods.
 */

import { ApiClient } from "../lib/api-client";
import type {
  Task,
  TaskDetail,
  MatterDashboard,
  DocumentUploadURL,
  DocumentDetail,
  DocumentBrief,
  CommentBrief,
  Matter,
} from "../lib/types";
import {
  TASK_PHASE_LABELS,
  TASK_PHASE_ORDER,
  TASK_STATUS_LABELS,
  TASK_PRIORITY_LABELS,
  PHASE_LABELS,
} from "../lib/constants";

// ─── Task Phase Constants ───────────────────────────────────────────────────

describe("Task Phase Constants", () => {
  it("should have labels for all phases", () => {
    for (const phase of TASK_PHASE_ORDER) {
      expect(TASK_PHASE_LABELS[phase]).toBeDefined();
    }
  });

  it("should have 9 phases in order", () => {
    expect(TASK_PHASE_ORDER).toHaveLength(9);
    expect(TASK_PHASE_ORDER[0]).toBe("immediate");
    expect(TASK_PHASE_ORDER[TASK_PHASE_ORDER.length - 1]).toBe("custom");
  });

  it("should have transfer_distribution phase", () => {
    expect(TASK_PHASE_LABELS["transfer_distribution"]).toBe("Transfer & Distribution");
  });
});

// ─── Task Types ─────────────────────────────────────────────────────────────

describe("Task Types", () => {
  it("should create a valid Task with all fields", () => {
    const task: Task = {
      id: "t1",
      matter_id: "m1",
      title: "File probate petition",
      description: "File with county court",
      instructions: "Use Form DE-111",
      phase: "probate_filing",
      status: "not_started",
      priority: "critical",
      assigned_to: null,
      due_date: "2026-04-15",
      requires_document: true,
      completed_at: null,
      sort_order: 1,
      metadata: {},
      documents: [],
      dependencies: [],
      created_at: "2026-01-15T10:00:00Z",
      updated_at: "2026-01-15T10:00:00Z",
    };
    expect(task.requires_document).toBe(true);
    expect(task.documents).toHaveLength(0);
  });

  it("should create a valid TaskDetail with comments", () => {
    const task: TaskDetail = {
      id: "t1",
      matter_id: "m1",
      title: "Review trust document",
      description: null,
      instructions: null,
      phase: "asset_inventory",
      status: "in_progress",
      priority: "normal",
      assigned_to: "user-1",
      due_date: null,
      requires_document: false,
      completed_at: null,
      sort_order: 5,
      metadata: {},
      documents: [
        { id: "d1", filename: "trust.pdf", doc_type: "trust_document", created_at: "2026-01-20T10:00:00Z" },
      ],
      dependencies: [],
      dependents: ["t2"],
      comments: [
        { id: "c1", author_id: "u1", body: "Started review", created_at: "2026-02-01T10:00:00Z" },
      ],
      created_at: "2026-01-15T10:00:00Z",
      updated_at: "2026-02-01T10:00:00Z",
    };
    expect(task.dependents).toHaveLength(1);
    expect(task.comments).toHaveLength(1);
    expect(task.documents).toHaveLength(1);
  });
});

// ─── Document Types ─────────────────────────────────────────────────────────

describe("Document Types", () => {
  it("should create a valid DocumentUploadURL", () => {
    const url: DocumentUploadURL = {
      upload_url: "https://s3.example.com/upload",
      storage_key: "documents/abc123.pdf",
      expires_in: 900,
    };
    expect(url.expires_in).toBe(900);
  });

  it("should create a valid DocumentDetail", () => {
    const doc: DocumentDetail = {
      id: "d1",
      matter_id: "m1",
      filename: "death_certificate.pdf",
      storage_key: "documents/d1.pdf",
      mime_type: "application/pdf",
      size_bytes: 102400,
      doc_type: "death_certificate",
      created_at: "2026-01-15T10:00:00Z",
    };
    expect(doc.mime_type).toBe("application/pdf");
  });
});

// ─── MatterDashboard ────────────────────────────────────────────────────────

describe("MatterDashboard", () => {
  it("should have task_summary with completion_percentage", () => {
    const dashboard: MatterDashboard = {
      matter: {
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
      },
      task_summary: {
        total: 20,
        not_started: 5,
        in_progress: 8,
        blocked: 2,
        complete: 5,
        waived: 0,
        overdue: 3,
        completion_percentage: 25,
      },
      asset_summary: {
        total_count: 10,
        total_estimated_value: 2500000,
        by_type: { real_estate: 3, bank_account: 5 },
        by_status: { discovered: 4, valued: 6 },
      },
      stakeholder_count: 5,
      upcoming_deadlines: [
        { id: "dl1", matter_id: "m1", title: "IRS Form 706", due_date: "2026-06-15", status: "upcoming" },
      ],
      recent_events: [],
    };
    expect(dashboard.task_summary.completion_percentage).toBe(25);
    expect(dashboard.upcoming_deadlines).toHaveLength(1);
  });
});

// ─── API Client Methods ─────────────────────────────────────────────────────

describe("ApiClient - Matter & Task Methods", () => {
  const client = new ApiClient({
    baseUrl: "http://test",
    getAccessToken: async () => null,
  });

  it("should have getTask method", () => {
    expect(typeof client.getTask).toBe("function");
  });

  it("should have completeTask method", () => {
    expect(typeof client.completeTask).toBe("function");
  });

  it("should have waiveTask method", () => {
    expect(typeof client.waiveTask).toBe("function");
  });

  it("should have getUploadUrl method", () => {
    expect(typeof client.getUploadUrl).toBe("function");
  });

  it("should have registerDocument method", () => {
    expect(typeof client.registerDocument).toBe("function");
  });

  it("should have linkTaskDocument method", () => {
    expect(typeof client.linkTaskDocument).toBe("function");
  });

  it("should have getMatterDashboard method", () => {
    expect(typeof client.getMatterDashboard).toBe("function");
  });
});

// ─── Navigation State ───────────────────────────────────────────────────────

describe("Navigation", () => {
  it("should define valid screen types", () => {
    // These match the Screen type union in (tabs)/index.tsx
    const screens = [
      { name: "list" as const },
      { name: "detail" as const, matterId: "m1" },
      { name: "tasks" as const, matterId: "m1" },
      { name: "taskDetail" as const, matterId: "m1", taskId: "t1" },
    ];
    expect(screens).toHaveLength(4);
    expect(screens[3]!.name).toBe("taskDetail");
  });
});
