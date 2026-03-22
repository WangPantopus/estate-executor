import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/layout/Toaster";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { SocketProvider } from "@/components/providers/SocketProvider";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ToastProvider>
      <SocketProvider>
        <AppShell>
          {children}
          <CommandPalette />
        </AppShell>
      </SocketProvider>
    </ToastProvider>
  );
}
