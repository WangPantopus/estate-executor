/**
 * Estate Executor OS — Mobile TypeScript Types
 *
 * Mirrors the web frontend types. Keep in sync with
 * frontend/src/lib/types.ts and backend schemas.
 */

// ─── Enums ──────────────────────────────────────────────────────────────────

export type MatterStatus = "active" | "on_hold" | "closed" | "archived";
export type MatterPhase = "immediate" | "administration" | "distribution" | "closing";
export type EstateType =
  | "testate_probate"
  | "intestate_probate"
  | "trust_administration"
  | "conservatorship"
  | "mixed_probate_trust"
  | "other";
export type StakeholderRole = "matter_admin" | "professional" | "executor_trustee" | "beneficiary" | "read_only";
export type TaskStatus = "not_started" | "in_progress" | "blocked" | "complete" | "waived" | "cancelled";
export type TaskPriority = "critical" | "normal" | "informational";
export type TaskPhase =
  | "immediate"
  | "asset_inventory"
  | "notification"
  | "probate_filing"
  | "tax"
  | "transfer_distribution"
  | "family_communication"
  | "closing"
  | "custom";
export type CommunicationType = "message" | "milestone_notification" | "distribution_notice" | "document_request" | "dispute_flag";

// ─── Common ─────────────────────────────────────────────────────────────────

export interface PaginationMeta {
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

// ─── Auth ───────────────────────────────────────────────────────────────────

export interface FirmMembershipDetail {
  firm_id: string;
  firm_name: string;
  firm_slug: string;
  firm_role: string;
}

export interface UserProfile {
  user_id: string;
  email: string;
  full_name: string;
  firm_memberships: FirmMembershipDetail[];
}

// ─── Matters ────────────────────────────────────────────────────────────────

export interface Matter {
  id: string;
  firm_id: string;
  title: string;
  status: MatterStatus;
  estate_type: EstateType;
  jurisdiction_state: string;
  date_of_death: string | null;
  decedent_name: string;
  estimated_value: number | null;
  phase: MatterPhase;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface TaskSummary {
  total: number;
  not_started: number;
  in_progress: number;
  blocked: number;
  complete: number;
  waived: number;
  overdue: number;
  completion_percentage: number;
}

export interface AssetSummary {
  total_count: number;
  total_estimated_value: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
}

export interface DeadlineResponse {
  id: string;
  matter_id: string;
  title: string;
  due_date: string;
  status: string;
}

export interface EventResponse {
  id: string;
  matter_id: string;
  actor_name: string | null;
  entity_type: string;
  action: string;
  created_at: string;
}

export interface MatterDashboard {
  matter: Matter;
  task_summary: TaskSummary;
  asset_summary: AssetSummary;
  stakeholder_count: number;
  upcoming_deadlines: DeadlineResponse[];
  recent_events: EventResponse[];
}

// ─── Tasks ──────────────────────────────────────────────────────────────────

export interface Task {
  id: string;
  matter_id: string;
  title: string;
  description: string | null;
  phase: TaskPhase;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_to: string | null;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
}

// ─── Communications ─────────────────────────────────────────────────────────

export interface CommunicationResponse {
  id: string;
  matter_id: string;
  sender_id: string;
  sender_name: string;
  type: CommunicationType;
  subject: string | null;
  body: string;
  visibility: string;
  acknowledged_by: string[];
  created_at: string;
}

// ─── Notifications (local type for mobile) ──────────────────────────────────

export interface AppNotification {
  id: string;
  title: string;
  body: string;
  type: "deadline" | "task" | "communication" | "distribution";
  matter_id: string;
  matter_title: string;
  created_at: string;
  read: boolean;
}
