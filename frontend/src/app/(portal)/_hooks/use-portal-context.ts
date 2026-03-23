"use client";

import { useMemo } from "react";
import { usePathname } from "next/navigation";
import { useCurrentUser, useMatterDashboard, useStakeholders } from "@/hooks";

const FIRM_ID = "current";

/**
 * Provides portal-scoped context: matter title, user info, firm branding,
 * and the current user's stakeholder record.
 */
export function usePortalContext() {
  const pathname = usePathname();
  const { data: currentUser, isLoading: userLoading } = useCurrentUser();

  // Extract matterId from /portal/{matterId}/...
  const matterId = useMemo(() => {
    const match = pathname.match(/^\/portal\/([^/]+)/);
    return match?.[1] ?? "";
  }, [pathname]);

  const { data: dashboard, isLoading: dashboardLoading } = useMatterDashboard(
    FIRM_ID,
    matterId,
  );
  const { data: stakeholdersData, isLoading: stakeholdersLoading } =
    useStakeholders(FIRM_ID, matterId);

  const matter = dashboard?.matter;

  // Find the current user's stakeholder record
  const currentStakeholder = useMemo(() => {
    if (!currentUser || !stakeholdersData?.data) return null;
    return (
      stakeholdersData.data.find(
        (s) =>
          s.email === currentUser.email || s.user_id === currentUser.user_id,
      ) ?? null
    );
  }, [currentUser, stakeholdersData]);

  // Find the lead professional (matter_admin or professional)
  const leadProfessional = useMemo(() => {
    if (!stakeholdersData?.data) return null;
    return (
      stakeholdersData.data.find(
        (s) => s.role === "matter_admin" || s.role === "professional",
      ) ?? null
    );
  }, [stakeholdersData]);

  // Firm branding — placeholder until firm white_label config is surfaced
  const firmLogoUrl: string | null = null;
  const firmName = "Estate Executor OS";

  return {
    matterId,
    matter,
    matterTitle: matter
      ? `Estate of ${matter.decedent_name}`
      : "Loading...",
    userName: currentUser?.full_name ?? currentUser?.email ?? "User",
    userEmail: currentUser?.email ?? "",
    currentStakeholder,
    leadProfessional,
    firmLogoUrl: firmLogoUrl ?? null,
    firmName,
    dashboard,
    isLoading: userLoading || dashboardLoading || stakeholdersLoading,
  };
}
