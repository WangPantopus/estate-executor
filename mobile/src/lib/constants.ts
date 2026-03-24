/**
 * Shared constants for the mobile app.
 */

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const PHASE_LABELS: Record<string, string> = {
  immediate: "Immediate",
  administration: "Administration",
  distribution: "Distribution",
  closing: "Closing",
};

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
  informational: "Info",
};

export const ESTATE_TYPE_LABELS: Record<string, string> = {
  testate_probate: "Probate (with Will)",
  intestate_probate: "Probate (no Will)",
  trust_administration: "Trust Administration",
  conservatorship: "Conservatorship",
  mixed_probate_trust: "Probate + Trust",
  other: "Other",
};
