"use client";

import { useMemo } from "react";
import { useCurrentUser, useStakeholders } from "./use-queries";
import type { StakeholderRole } from "@/lib/types";

const FIRM_ID = "current";

/**
 * Permission definitions matching the backend ROLE_PERMISSIONS.
 * Maps each role to its allowed permissions (hierarchical).
 */
const ROLE_PERMISSIONS: Record<StakeholderRole, string[]> = {
  matter_admin: [
    "matter:read", "matter:write", "matter:close",
    "task:read", "task:write", "task:assign", "task:complete",
    "asset:read", "asset:write",
    "entity:read", "entity:write",
    "document:read", "document:upload", "document:download",
    "stakeholder:invite", "stakeholder:manage",
    "communication:read", "communication:write",
    "event:read",
    "ai:trigger",
    "report:generate",
  ],
  professional: [
    "matter:read",
    "task:read", "task:write", "task:assign", "task:complete",
    "asset:read", "asset:write",
    "entity:read", "entity:write",
    "document:read", "document:upload", "document:download",
    "communication:read", "communication:write",
    "event:read",
    "ai:trigger",
    "report:generate",
  ],
  executor_trustee: [
    "matter:read",
    "task:read:assigned", "task:complete:assigned",
    "asset:read",
    "document:read:linked", "document:upload",
    "communication:read", "communication:write",
  ],
  beneficiary: [
    "matter:read:summary",
    "task:read:milestones",
    "document:read:shared",
    "communication:read:visible",
  ],
  read_only: [
    "matter:read:summary",
    "task:read:milestones",
  ],
};

function hasPermission(role: StakeholderRole, required: string): boolean {
  const permissions = ROLE_PERMISSIONS[role] || [];
  for (const perm of permissions) {
    if (perm === required) return true;
    // Hierarchical: "task:read" grants "task:read:assigned"
    if (required.startsWith(perm + ":")) return true;
  }
  return false;
}

export interface PermissionInfo {
  /** Current user's role on this matter */
  role: StakeholderRole | null;
  /** Whether permissions are still loading */
  isLoading: boolean;
  /** Check if the current user has a specific permission */
  can: (permission: string) => boolean;
  /** Whether the user is a matter admin */
  isAdmin: boolean;
  /** Whether the user is a professional */
  isProfessional: boolean;
  /** Whether the user is an executor/trustee */
  isExecutor: boolean;
  /** Whether the user is a beneficiary */
  isBeneficiary: boolean;
  /** Whether the user is read-only */
  isReadOnly: boolean;
  /** Whether the user can write (admin or professional) */
  canWrite: boolean;
}

/**
 * Hook that returns the current user's role and permissions for a specific matter.
 *
 * Resolves the user's stakeholder record to determine their role,
 * then provides permission checks matching the backend enforcement.
 */
export function usePermissions(matterId: string): PermissionInfo {
  const { data: currentUser, isLoading: userLoading } = useCurrentUser();
  const { data: stakeholders, isLoading: stakeholdersLoading } =
    useStakeholders(FIRM_ID, matterId);

  const isLoading = userLoading || stakeholdersLoading;

  const role = useMemo<StakeholderRole | null>(() => {
    if (!currentUser || !stakeholders?.data) return null;

    // Find the stakeholder record matching the current user
    const match = stakeholders.data.find(
      (s) => s.email === currentUser.email || s.user_id === currentUser.user_id,
    );

    return match?.role ?? "matter_admin"; // fallback for firm members
  }, [currentUser, stakeholders]);

  const can = useMemo(() => {
    if (!role) return () => false;
    return (permission: string) => hasPermission(role, permission);
  }, [role]);

  return {
    role,
    isLoading,
    can,
    isAdmin: role === "matter_admin",
    isProfessional: role === "professional",
    isExecutor: role === "executor_trustee",
    isBeneficiary: role === "beneficiary",
    isReadOnly: role === "read_only",
    canWrite: role === "matter_admin" || role === "professional",
  };
}
