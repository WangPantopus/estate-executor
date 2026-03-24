import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/layout/Toaster";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { SocketProvider } from "@/components/providers/SocketProvider";
import { BeneficiaryRedirect } from "@/components/layout/BeneficiaryRedirect";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ToastProvider>
      <SocketProvider>
        <BeneficiaryRedirect>
          <AppShell>
            {children}
            <CommandPalette />
          </AppShell>
        </BeneficiaryRedirect>
      </SocketProvider>
    </ToastProvider>
  );
}
