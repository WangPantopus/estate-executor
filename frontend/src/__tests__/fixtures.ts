/**
 * Shared test fixtures and mock data for frontend tests.
 */

import type {
  Matter,
  MatterDashboard,
  Task,
  TaskDetail,
  AssetListItem,
  DeadlineResponse,
  CalendarMonth,
  CommunicationResponse,
  Stakeholder,
  PaginatedResponse,
  TaskSummary,
  AssetSummary,
  EventResponse,
  UserProfile,
} from "@/lib/types";

// ─── Users ───────────────────────────────────────────────────────────────────

export const mockUser: UserProfile = {
  user_id: "user-1",
  email: "admin@example.com",
  full_name: "Test Admin",
  avatar_url: null,
  firm_memberships: [
    { firm_id: "firm-1", firm_name: "Test Law Firm", firm_role: "owner" },
  ],
};

// ─── Matters ─────────────────────────────────────────────────────────────────

export const mockMatter: Matter = {
  id: "matter-1",
  firm_id: "firm-1",
  title: "Estate of John Doe",
  status: "active",
  estate_type: "testate_probate",
  jurisdiction_state: "CA",
  decedent_name: "John Doe",
  date_of_death: "2025-12-01",
  date_of_incapacity: null,
  estimated_value: 2500000,
  phase: "administration",
  settings: {},
  closed_at: null,
  created_at: "2025-12-15T10:00:00Z",
  updated_at: "2026-01-10T10:00:00Z",
};

export const mockMatter2: Matter = {
  ...mockMatter,
  id: "matter-2",
  title: "Estate of Jane Smith",
  status: "on_hold",
  jurisdiction_state: "NY",
  decedent_name: "Jane Smith",
  estimated_value: 800000,
  phase: "immediate",
};

export const mockMatter3: Matter = {
  ...mockMatter,
  id: "matter-3",
  title: "Estate of Bob Wilson",
  status: "closed",
  jurisdiction_state: "TX",
  decedent_name: "Bob Wilson",
  estimated_value: 5000000,
  phase: "closing",
  closed_at: "2026-03-01T10:00:00Z",
};

export const mockMattersPage: PaginatedResponse<Matter> = {
  data: [mockMatter, mockMatter2, mockMatter3],
  meta: { total: 3, page: 1, page_size: 25, total_pages: 1 },
};

// ─── Tasks ───────────────────────────────────────────────────────────────────

export const mockTaskSummary: TaskSummary = {
  total: 10,
  not_started: 2,
  in_progress: 3,
  blocked: 1,
  complete: 3,
  waived: 1,
  overdue: 2,
  completion_percentage: 40,
};

export const mockTask1: Task = {
  id: "task-1",
  matter_id: "matter-1",
  title: "Obtain Death Certificate",
  description: "Get certified copies of the death certificate",
  phase: "immediate",
  status: "complete",
  priority: "critical",
  assigned_to: "user-1",
  assignee_name: "Test Admin",
  due_date: "2026-01-15",
  requires_document: true,
  is_system_generated: true,
  sort_order: 1,
  dependencies: [],
  dependent_count: 2,
  document_count: 1,
  documents: [],
  created_at: "2025-12-15T10:00:00Z",
  updated_at: "2026-01-10T10:00:00Z",
  completed_at: "2026-01-10T10:00:00Z",
  waived_at: null,
  waived_reason: null,
};

export const mockTask2: Task = {
  ...mockTask1,
  id: "task-2",
  title: "File Probate Petition",
  description: "File the initial probate petition with the court",
  phase: "probate_filing",
  status: "in_progress",
  priority: "high",
  due_date: "2026-03-01",
  dependencies: ["task-1"],
  dependent_count: 0,
  document_count: 0,
  completed_at: null,
};

export const mockTask3: Task = {
  ...mockTask1,
  id: "task-3",
  title: "Inventory Personal Property",
  description: "Create detailed inventory of personal items",
  phase: "asset_inventory",
  status: "not_started",
  priority: "medium",
  due_date: "2026-04-01",
  dependencies: [],
  dependent_count: 0,
  document_count: 0,
  completed_at: null,
};

export const mockTask4: Task = {
  ...mockTask1,
  id: "task-4",
  title: "Blocked Task",
  description: "This task is blocked",
  phase: "administration",
  status: "blocked",
  priority: "high",
  due_date: "2026-05-01",
  dependencies: ["task-2"],
  dependent_count: 0,
  document_count: 0,
  completed_at: null,
};

export const mockTaskDetail: TaskDetail = {
  ...mockTask2,
  instructions: "File with the Superior Court in the county of last residence.",
  dependents: [],
  comments: [],
};

export const mockTasksPage: PaginatedResponse<Task> = {
  data: [mockTask1, mockTask2, mockTask3, mockTask4],
  meta: { total: 4, page: 1, page_size: 25, total_pages: 1 },
};

// ─── Assets ──────────────────────────────────────────────────────────────────

export const mockAssetSummary: AssetSummary = {
  total_count: 5,
  total_estimated_value: 2500000,
  by_type: { real_estate: 1, bank_account: 2, brokerage_account: 1, life_insurance: 1 },
  by_status: { discovered: 2, valued: 2, transferred: 1 },
};

export const mockAsset1: AssetListItem = {
  id: "asset-1",
  matter_id: "matter-1",
  title: "Primary Residence",
  asset_type: "real_estate",
  status: "valued",
  institution: null,
  account_number_masked: null,
  current_estimated_value: 850000,
  date_of_death_value: 800000,
  ownership_type: "individual",
  transfer_mechanism: "probate",
  entities: [{ id: "entity-1", name: "Doe Family Trust" }],
  document_count: 3,
  created_at: "2025-12-20T10:00:00Z",
  updated_at: "2026-01-05T10:00:00Z",
};

export const mockAsset2: AssetListItem = {
  id: "asset-2",
  matter_id: "matter-1",
  title: "Checking Account",
  asset_type: "bank_account",
  status: "discovered",
  institution: "Chase Bank",
  account_number_masked: "****4567",
  current_estimated_value: 45000,
  date_of_death_value: 42000,
  ownership_type: "joint_tenancy",
  transfer_mechanism: "beneficiary_designation",
  entities: [],
  document_count: 0,
  created_at: "2025-12-22T10:00:00Z",
  updated_at: "2026-01-03T10:00:00Z",
};

// ─── Deadlines ───────────────────────────────────────────────────────────────

export const mockDeadline1: DeadlineResponse = {
  id: "dl-1",
  matter_id: "matter-1",
  task_id: null,
  title: "Federal Estate Tax Return",
  description: "Form 706 due 9 months from DOD",
  due_date: "2026-09-01",
  source: "auto",
  rule: null,
  status: "upcoming",
  assigned_to: null,
  assignee_name: null,
  reminder_config: { days_before: [30, 7, 1] },
  task: null,
  created_at: "2025-12-15T10:00:00Z",
  updated_at: "2025-12-15T10:00:00Z",
};

export const mockDeadline2: DeadlineResponse = {
  ...mockDeadline1,
  id: "dl-2",
  title: "State Inheritance Tax",
  due_date: "2026-04-15",
  status: "upcoming",
};

export const mockDeadline3: DeadlineResponse = {
  ...mockDeadline1,
  id: "dl-3",
  title: "Creditor Claims Window",
  due_date: "2026-06-15",
  status: "completed",
};

export const mockCalendarMonths: CalendarMonth[] = [
  {
    month: "2026-04",
    deadlines: [
      {
        id: "dl-2",
        title: "State Inheritance Tax",
        due_date: "2026-04-15",
        status: "upcoming",
        source: "auto",
      },
    ],
  },
  {
    month: "2026-06",
    deadlines: [
      {
        id: "dl-3",
        title: "Creditor Claims Window",
        due_date: "2026-06-15",
        status: "completed",
        source: "auto",
      },
    ],
  },
];

// ─── Communications ──────────────────────────────────────────────────────────

export const mockMessage1: CommunicationResponse = {
  id: "msg-1",
  matter_id: "matter-1",
  type: "message",
  subject: "Initial Consultation Notes",
  body: "Summary of the initial meeting with the family.",
  visibility: "all",
  sender_id: "user-1",
  sender_name: "Test Admin",
  sender_type: "user",
  recipients: [],
  is_flagged: false,
  flag_reason: null,
  acknowledged_by: [],
  created_at: "2026-01-10T10:00:00Z",
};

export const mockMessage2: CommunicationResponse = {
  ...mockMessage1,
  id: "msg-2",
  type: "milestone",
  subject: "Probate Petition Filed",
  body: "The probate petition has been filed with the court.",
  visibility: "all",
  created_at: "2026-02-15T10:00:00Z",
};

export const mockMessage3: CommunicationResponse = {
  ...mockMessage1,
  id: "msg-3",
  type: "message",
  subject: "Fee Breakdown for Review",
  body: "Attached is the detailed fee breakdown for professional review.",
  visibility: "professionals_only",
  created_at: "2026-03-01T10:00:00Z",
};

// ─── Stakeholders ────────────────────────────────────────────────────────────

export const mockStakeholders: PaginatedResponse<Stakeholder> = {
  data: [
    {
      id: "sh-1",
      matter_id: "matter-1",
      user_id: "user-1",
      email: "admin@example.com",
      full_name: "Test Admin",
      role: "matter_admin",
      invite_status: "accepted",
      invited_by: null,
      accepted_at: "2025-12-15T10:00:00Z",
      created_at: "2025-12-15T10:00:00Z",
      updated_at: "2025-12-15T10:00:00Z",
    },
    {
      id: "sh-2",
      matter_id: "matter-1",
      user_id: "user-2",
      email: "beneficiary@example.com",
      full_name: "Jane Beneficiary",
      role: "beneficiary",
      invite_status: "accepted",
      invited_by: "user-1",
      accepted_at: "2025-12-20T10:00:00Z",
      created_at: "2025-12-20T10:00:00Z",
      updated_at: "2025-12-20T10:00:00Z",
    },
  ],
  meta: { total: 2, page: 1, page_size: 25, total_pages: 1 },
};

// ─── Events ──────────────────────────────────────────────────────────────────

export const mockEvents: PaginatedResponse<EventResponse> = {
  data: [
    {
      id: "evt-1",
      matter_id: "matter-1",
      entity_type: "task",
      entity_id: "task-1",
      action: "completed",
      changes: null,
      actor_id: "user-1",
      actor_type: "user",
      actor_name: "Test Admin",
      created_at: "2026-01-10T10:00:00Z",
    },
  ],
  meta: { total: 1, page: 1, page_size: 25, total_pages: 1 },
};

// ─── Dashboard ───────────────────────────────────────────────────────────────

export const mockDashboard: MatterDashboard = {
  matter: mockMatter,
  task_summary: mockTaskSummary,
  asset_summary: mockAssetSummary,
  stakeholder_count: 2,
  upcoming_deadlines: [mockDeadline1, mockDeadline2],
  recent_events: mockEvents.data,
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

export const FIRM_ID = "current";
export const MATTER_ID = "matter-1";
