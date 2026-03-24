"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useApi } from "@/hooks/use-api";

/**
 * Client component that checks if the user is a beneficiary-only user.
 * If they have beneficiary matters and no firm memberships, redirect to portal.
 * Placed in the dashboard layout to intercept beneficiary logins.
 */
export function BeneficiaryRedirect({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const api = useApi();
  const [checked, setChecked] = useState(() =>
    // Skip check for routes that don't need redirect
    pathname.startsWith("/portal") || pathname.startsWith("/auth") || pathname.startsWith("/invite"),
  );
  const checking = useRef(false);

  useEffect(() => {
    if (checked || checking.current) return;
    checking.current = true;

    let cancelled = false;

    async function checkBeneficiary() {
      try {
        const [profile, portalMatters] = await Promise.all([
          api.getMe(),
          api.getPortalMatters(),
        ]);

        if (cancelled) return;

        // If user has no firm memberships and has portal matters, they're beneficiary-only
        const hasFirmAccess = profile.firm_memberships.length > 0;
        const hasPortalMatters = (portalMatters.matters?.length ?? 0) > 0;

        if (!hasFirmAccess && hasPortalMatters) {
          if (portalMatters.matters.length === 1) {
            router.replace(`/portal/${portalMatters.matters[0].matter_id}`);
          } else {
            router.replace("/portal");
          }
          return;
        }
      } catch {
        // If API fails, just show the dashboard
      }
      if (!cancelled) {
        setChecked(true);
      }
    }

    checkBeneficiary();
    return () => {
      cancelled = true;
    };
  }, [api, checked, pathname, router]);

  if (!checked) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin h-8 w-8 rounded-full border-4 border-gray-200 border-t-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
