import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/layout/Toaster";
import { CommandPalette } from "@/components/layout/CommandPalette";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ToastProvider>
      <AppShell>
        {children}
        <CommandPalette />
      </AppShell>
    </ToastProvider>
  );
}
