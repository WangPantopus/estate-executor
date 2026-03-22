"use client";

import { useSocket, type ConnectionStatus as Status } from "@/components/providers/SocketProvider";
import { cn } from "@/lib/utils";
import { Wifi, WifiOff } from "lucide-react";

/**
 * Subtle connection status indicator for the app header.
 *
 * - Green dot: connected (real-time updates active)
 * - Pulsing amber dot: connecting/reconnecting
 * - Hidden when disconnected (graceful degradation)
 */
export function ConnectionStatus() {
  const { status } = useSocket();

  if (status === "disconnected") {
    return null;
  }

  return (
    <div
      className="flex items-center gap-1.5"
      title={statusLabel(status)}
      aria-label={statusLabel(status)}
    >
      <span
        className={cn(
          "size-2 rounded-full",
          status === "connected" && "bg-success",
          status === "connecting" && "bg-warning animate-pulse",
        )}
      />
      <span className="hidden lg:inline text-[11px] text-muted-foreground">
        {status === "connected" ? "Live" : "Reconnecting..."}
      </span>
    </div>
  );
}

function statusLabel(status: Status): string {
  switch (status) {
    case "connected":
      return "Real-time updates active";
    case "connecting":
      return "Reconnecting to real-time updates...";
    case "disconnected":
      return "Real-time updates unavailable";
  }
}
