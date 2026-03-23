"use client";

import { use, type ReactNode } from "react";
import { useMatterSocket } from "@/hooks/use-matter-socket";

/**
 * Portal matter layout — joins the WebSocket room for real-time updates.
 */
export default function PortalMatterLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = use(params);

  // Subscribe to real-time updates for this matter
  useMatterSocket(matterId);

  return <>{children}</>;
}
