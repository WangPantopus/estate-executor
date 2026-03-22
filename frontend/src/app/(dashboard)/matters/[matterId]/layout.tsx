"use client";

import { useMatterSocket } from "@/hooks/use-matter-socket";
import { use } from "react";

/**
 * Matter layout — wraps all matter sub-pages with real-time WebSocket updates.
 *
 * Automatically joins the matter room on mount and leaves on unmount.
 * All child pages receive live updates via TanStack Query invalidation.
 */
export default function MatterLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);

  // Subscribe to real-time updates for this matter
  useMatterSocket(matterId);

  return <>{children}</>;
}
