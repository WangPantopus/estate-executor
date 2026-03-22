import type { EstateType, AssetType } from "./types";

export const US_STATES = [
  { value: "AL", label: "Alabama" },
  { value: "AK", label: "Alaska" },
  { value: "AZ", label: "Arizona" },
  { value: "AR", label: "Arkansas" },
  { value: "CA", label: "California" },
  { value: "CO", label: "Colorado" },
  { value: "CT", label: "Connecticut" },
  { value: "DE", label: "Delaware" },
  { value: "DC", label: "District of Columbia" },
  { value: "FL", label: "Florida" },
  { value: "GA", label: "Georgia" },
  { value: "HI", label: "Hawaii" },
  { value: "ID", label: "Idaho" },
  { value: "IL", label: "Illinois" },
  { value: "IN", label: "Indiana" },
  { value: "IA", label: "Iowa" },
  { value: "KS", label: "Kansas" },
  { value: "KY", label: "Kentucky" },
  { value: "LA", label: "Louisiana" },
  { value: "ME", label: "Maine" },
  { value: "MD", label: "Maryland" },
  { value: "MA", label: "Massachusetts" },
  { value: "MI", label: "Michigan" },
  { value: "MN", label: "Minnesota" },
  { value: "MS", label: "Mississippi" },
  { value: "MO", label: "Missouri" },
  { value: "MT", label: "Montana" },
  { value: "NE", label: "Nebraska" },
  { value: "NV", label: "Nevada" },
  { value: "NH", label: "New Hampshire" },
  { value: "NJ", label: "New Jersey" },
  { value: "NM", label: "New Mexico" },
  { value: "NY", label: "New York" },
  { value: "NC", label: "North Carolina" },
  { value: "ND", label: "North Dakota" },
  { value: "OH", label: "Ohio" },
  { value: "OK", label: "Oklahoma" },
  { value: "OR", label: "Oregon" },
  { value: "PA", label: "Pennsylvania" },
  { value: "RI", label: "Rhode Island" },
  { value: "SC", label: "South Carolina" },
  { value: "SD", label: "South Dakota" },
  { value: "TN", label: "Tennessee" },
  { value: "TX", label: "Texas" },
  { value: "UT", label: "Utah" },
  { value: "VT", label: "Vermont" },
  { value: "VA", label: "Virginia" },
  { value: "WA", label: "Washington" },
  { value: "WV", label: "West Virginia" },
  { value: "WI", label: "Wisconsin" },
  { value: "WY", label: "Wyoming" },
] as const;

export const ESTATE_TYPE_LABELS: Record<EstateType, { label: string; description: string }> = {
  testate_probate: {
    label: "Probate — with Will",
    description: "Decedent left a valid will to be probated",
  },
  intestate_probate: {
    label: "Probate — without Will",
    description: "No will exists; estate distributed per state intestacy law",
  },
  trust_administration: {
    label: "Trust Administration",
    description: "Assets held in a revocable or irrevocable trust",
  },
  mixed_probate_trust: {
    label: "Probate + Trust",
    description: "Estate includes both probate assets and trust-held assets",
  },
  conservatorship: {
    label: "Conservatorship / Incapacity",
    description: "Managing affairs for a living but incapacitated person",
  },
  other: {
    label: "Other",
    description: "Other estate administration type",
  },
};

export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  real_estate: "Real estate",
  bank_account: "Bank accounts",
  brokerage_account: "Investment / brokerage accounts",
  retirement_account: "Retirement accounts (IRA, 401k, etc.)",
  life_insurance: "Life insurance policies",
  business_interest: "Business interests",
  vehicle: "Vehicles",
  digital_asset: "Digital assets",
  personal_property: "Significant personal property",
  receivable: "Receivables",
  other: "Other",
};

export const MATTER_FLAGS = [
  { key: "multi_state_assets", label: "Multi-state assets" },
  { key: "business_ownership", label: "Business ownership involved" },
  { key: "minor_beneficiaries", label: "Minor beneficiaries" },
  { key: "special_needs_beneficiary", label: "Special needs beneficiary" },
  { key: "potential_estate_tax", label: "Potential estate tax liability" },
] as const;

export const PHASE_LABELS: Record<string, string> = {
  immediate: "Immediate",
  administration: "Administration",
  distribution: "Distribution",
  closing: "Closing",
};

export const TASK_PHASE_LABELS: Record<string, string> = {
  immediate: "Immediate",
  asset_inventory: "Asset Inventory",
  notification: "Notification",
  probate_filing: "Probate Filing",
  tax: "Tax",
  transfer_distribution: "Transfer & Distribution",
  family_communication: "Family Communication",
  closing: "Closing",
  custom: "Custom",
};

export const TASK_PHASE_ORDER: string[] = [
  "immediate",
  "asset_inventory",
  "notification",
  "probate_filing",
  "tax",
  "transfer_distribution",
  "family_communication",
  "closing",
  "custom",
];

export const TASK_STATUS_LABELS: Record<string, string> = {
  not_started: "Not Started",
  in_progress: "In Progress",
  blocked: "Blocked",
  complete: "Complete",
  waived: "Waived",
  cancelled: "Cancelled",
};

export const TASK_PRIORITY_LABELS: Record<string, string> = {
  critical: "Critical",
  normal: "Normal",
  informational: "Informational",
};

export const STAKEHOLDER_ROLE_LABELS: Record<string, string> = {
  matter_admin: "Matter Admin",
  professional: "Professional",
  executor_trustee: "Executor / Trustee",
  beneficiary: "Beneficiary",
  read_only: "Read Only",
};
