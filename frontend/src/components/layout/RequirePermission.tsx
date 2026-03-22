"use client";

import type { ReactNode } from "react";
import { usePermissions } from "@/hooks/use-permissions";

interface RequirePermissionProps {
  /** The permission string to check (e.g., "task:write", "stakeholder:manage") */
  permission: string;
  /** The matter ID to check permissions against */
  matterId: string;
  /** Content to render when permission is granted */
  children: ReactNode;
  /** Optional fallback to render when permission is denied (default: nothing) */
  fallback?: ReactNode;
}

/**
 * Conditionally renders children based on the current user's permissions.
 *
 * Usage:
 * ```tsx
 * <RequirePermission permission="stakeholder:manage" matterId={matterId}>
 *   <Button>Invite Stakeholder</Button>
 * </RequirePermission>
 * ```
 */
export function RequirePermission({
  permission,
  matterId,
  children,
  fallback = null,
}: RequirePermissionProps) {
  const { can, isLoading } = usePermissions(matterId);

  // While loading, render nothing (prevents flash of forbidden content)
  if (isLoading) return null;

  if (!can(permission)) return <>{fallback}</>;

  return <>{children}</>;
}

interface RoleGateProps {
  /** The matter ID to check role against */
  matterId: string;
  /** Roles that are allowed to see the content */
  allow?: string[];
  /** Roles that are denied from seeing the content */
  deny?: string[];
  /** Content to render when allowed */
  children: ReactNode;
  /** Optional fallback when denied */
  fallback?: ReactNode;
}

/**
 * Conditionally renders children based on the user's role (allow/deny lists).
 *
 * Usage:
 * ```tsx
 * <RoleGate matterId={matterId} allow={["matter_admin", "professional"]}>
 *   <EditButton />
 * </RoleGate>
 *
 * <RoleGate matterId={matterId} deny={["beneficiary", "read_only"]}>
 *   <DetailedView />
 * </RoleGate>
 * ```
 */
export function RoleGate({
  matterId,
  allow,
  deny,
  children,
  fallback = null,
}: RoleGateProps) {
  const { role, isLoading } = usePermissions(matterId);

  if (isLoading) return null;
  if (!role) return <>{fallback}</>;

  if (allow && !allow.includes(role)) return <>{fallback}</>;
  if (deny && deny.includes(role)) return <>{fallback}</>;

  return <>{children}</>;
}
