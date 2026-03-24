"use client";

import { initSentry } from "@/lib/sentry";

// Initialize Sentry at module load time rather than inside useEffect so that
// errors thrown during the initial render and hydration are captured.
// This module is "use client", so it only runs in the browser.
initSentry();

export function SentryProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
