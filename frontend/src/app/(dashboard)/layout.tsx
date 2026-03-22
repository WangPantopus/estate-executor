export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar will be added here */}
      <main className="flex-1">{children}</main>
    </div>
  );
}
