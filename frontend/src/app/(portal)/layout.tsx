"use client";

import React from "react";
import { ToastProvider } from "@/components/layout/Toaster";
import { SocketProvider } from "@/components/providers/SocketProvider";
import { PortalShell } from "./_components/PortalShell";

export default function PortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ToastProvider>
      <SocketProvider>
        <PortalShell>{children}</PortalShell>
      </SocketProvider>
    </ToastProvider>
  );
}
