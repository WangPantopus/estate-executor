/**
 * Shared TypeScript types matching backend schemas.
 * These will be expanded as API endpoints are built.
 */

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

export interface Firm {
  id: string;
  name: string;
  slug: string;
  type: FirmType;
  subscription_tier: string;
  created_at: string;
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
  estimated_value: number | null;
  phase: MatterPhase;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  matter_id: string;
  title: string;
  description: string | null;
  phase: string;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_to: string | null;
  due_date: string | null;
  requires_document: boolean;
  created_at: string;
  updated_at: string;
}
