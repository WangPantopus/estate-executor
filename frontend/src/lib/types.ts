/**
 * Shared TypeScript types matching backend Pydantic schemas.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type MatterStatus = "active" | "on_hold" | "closed" | "archived";

export type EstateType =
  | "testate_probate"
  | "intestate_probate"
  | "trust_administration"
  | "conservatorship"
  | "mixed_probate_trust"
  | "other";

export type MatterPhase =
  | "immediate"
  | "administration"
  | "distribution"
  | "closing";

export type TaskStatus =
  | "not_started"
  | "in_progress"
  | "blocked"
  | "complete"
  | "waived"
  | "cancelled";

export type TaskPriority = "critical" | "normal" | "informational";

export type StakeholderRole =
  | "matter_admin"
  | "professional"
  | "executor_trustee"
  | "beneficiary"
  | "read_only";

export type InviteStatus = "pending" | "accepted" | "revoked";

export type AssetType =
  | "real_estate"
  | "bank_account"
  | "brokerage_account"
  | "retirement_account"
  | "life_insurance"
  | "business_interest"
  | "vehicle"
  | "digital_asset"
  | "personal_property"
  | "receivable"
  | "other";

export type OwnershipType =
  | "in_trust"
  | "joint_tenancy"
  | "community_property"
  | "pod_tod"
  | "individual"
  | "business_owned"
  | "other";

export type FirmType =
  | "law_firm"
  | "ria"
  | "trust_company"
  | "family_office"
  | "other";

export type SubscriptionTier =
  | "starter"
  | "professional"
  | "growth"
  | "enterprise";

// ---------------------------------------------------------------------------
// Auth types
// ---------------------------------------------------------------------------

export interface FirmMembershipBrief {
  firm_id: string;
  firm_role: string;
}

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

export interface AcceptInviteResponse {
  stakeholder_id: string;
  matter_id: string;
  matter_title: string;
  role: string;
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

export interface Firm {
  id: string;
  name: string;
  slug: string;
  type: FirmType;
  subscription_tier: SubscriptionTier;
  settings: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Matter {
  id: string;
  firm_id: string;
  title: string;
  status: MatterStatus;
  estate_type: EstateType;
  jurisdiction_state: string;
  date_of_death: string | null;
  decedent_name: string;
  estimated_value: string | null;
  phase: MatterPhase;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface Task {
  id: string;
  matter_id: string;
  parent_task_id: string | null;
  template_key: string | null;
  title: string;
  description: string | null;
  instructions: string | null;
  phase: string;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_to: string | null;
  due_date: string | null;
  requires_document: boolean;
  completed_at: string | null;
  completed_by: string | null;
  sort_order: number;
  metadata: Record<string, unknown> | null;
  documents: DocumentBrief[];
  dependencies: string[];
  created_at: string;
  updated_at: string;
}

export interface DocumentBrief {
  id: string;
  filename: string;
  doc_type: string | null;
  created_at: string;
}

export interface Stakeholder {
  id: string;
  matter_id: string;
  user_id: string | null;
  email: string;
  full_name: string;
  role: StakeholderRole;
  relationship: string | null;
  invite_status: InviteStatus;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

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
