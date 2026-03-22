"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  Settings,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  ListTodo,
  Landmark,
  Building2,
  FileText,
  Calendar,
  MessageSquare,
  Activity,
  LogOut,
  User,
  ChevronDown,
  Menu,
  Search,
  LayoutGrid,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Sheet,
  SheetContent,
  SheetClose,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

// ─── Nav configuration ────────────────────────────────────────────────────────

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const mainNavItems: NavItem[] = [
  { label: "Dashboard", href: "/matters", icon: LayoutDashboard },
  { label: "Matters", href: "/matters", icon: Briefcase },
  { label: "Settings", href: "/settings", icon: Settings },
];

const matterNavItems: NavItem[] = [
  { label: "Overview", href: "", icon: LayoutGrid },
  { label: "Tasks", href: "/tasks", icon: ListTodo },
  { label: "Assets", href: "/assets", icon: Landmark },
  { label: "Entities", href: "/entities", icon: Building2 },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Calendar", href: "/deadlines", icon: Calendar },
  { label: "Communications", href: "/communications", icon: MessageSquare },
  { label: "Activity", href: "/activity", icon: Activity },
  { label: "Settings", href: "/settings", icon: Settings },
];

// Page label map for breadcrumbs
const PAGE_LABELS: Record<string, string> = {
  tasks: "Tasks",
  assets: "Assets",
  entities: "Entities",
  documents: "Documents",
  deadlines: "Calendar",
  communications: "Communications",
  activity: "Activity",
  settings: "Settings",
};

// ─── Helper: extract matter context from pathname ─────────────────────────────

function parseMatterContext(pathname: string) {
  const match = pathname.match(/^\/matters\/([^/]+)(\/(.*))?$/);
  if (!match) return null;
  return {
    matterId: match[1],
    subPage: match[3]?.split("/")[0] ?? null,
  };
}

// ─── Sidebar Nav Link ─────────────────────────────────────────────────────────

function SidebarLink({
  item,
  isActive,
  collapsed,
  onClick,
}: {
  item: NavItem;
  isActive: boolean;
  collapsed: boolean;
  onClick?: () => void;
}) {
  const link = (
    <Link
      href={item.href}
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors duration-150 relative",
        isActive
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
      )}
    >
      {isActive && (
        <div className="absolute left-0 top-1 bottom-1 w-[3px] rounded-full bg-gold" />
      )}
      <item.icon
        className={cn("size-[18px] shrink-0", isActive && "text-gold")}
      />
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{link}</TooltipTrigger>
        <TooltipContent side="right">{item.label}</TooltipContent>
      </Tooltip>
    );
  }

  return link;
}

// ─── Sidebar Content (shared between desktop and mobile) ──────────────────────

function SidebarContent({
  collapsed,
  pathname,
  matterContext,
  firmName,
  userName,
  userEmail,
  userAvatarUrl,
  onNavClick,
}: {
  collapsed: boolean;
  pathname: string;
  matterContext: ReturnType<typeof parseMatterContext>;
  firmName: string;
  userName: string;
  userEmail: string;
  userAvatarUrl?: string;
  onNavClick?: () => void;
}) {
  const userInitials = userName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const inMatter = !!matterContext;

  return (
    <>
      {/* Logo */}
      <div className="flex h-14 items-center px-5 shrink-0">
        {collapsed ? (
          <span className="text-lg font-semibold text-white">EE</span>
        ) : (
          <span className="text-base font-medium tracking-tight text-white">
            Estate Executor<span className="text-gold"> OS</span>
          </span>
        )}
      </div>

      {!collapsed && (
        <div className="px-5 pb-3">
          <p className="text-xs text-sidebar-muted truncate">{firmName}</p>
        </div>
      )}

      <Separator className="bg-sidebar-border" />

      {/* Navigation */}
      <ScrollArea className="flex-1 py-3">
        {inMatter ? (
          /* Matter-scoped navigation */
          <nav className="space-y-0.5 px-3">
            {/* Back to matters */}
            <Link
              href="/matters"
              onClick={onNavClick}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-xs text-sidebar-muted hover:text-sidebar-foreground transition-colors mb-2"
            >
              <ArrowLeft className="size-3.5" />
              {!collapsed && "Back to Matters"}
            </Link>

            {matterNavItems.map((item) => {
              const fullHref = `/matters/${matterContext.matterId}${item.href}`;
              const isActive = item.href === ""
                ? pathname === `/matters/${matterContext.matterId}`
                : pathname.startsWith(fullHref);

              return (
                <SidebarLink
                  key={item.href || "__overview"}
                  item={{ ...item, href: fullHref }}
                  isActive={isActive}
                  collapsed={collapsed}
                  onClick={onNavClick}
                />
              );
            })}
          </nav>
        ) : (
          /* Global navigation */
          <nav className="space-y-0.5 px-3">
            {mainNavItems.map((item) => {
              const isActive =
                pathname === item.href || pathname.startsWith(item.href + "/");

              return (
                <SidebarLink
                  key={item.href}
                  item={item}
                  isActive={isActive}
                  collapsed={collapsed}
                  onClick={onNavClick}
                />
              );
            })}
          </nav>
        )}
      </ScrollArea>

      {/* User section */}
      <Separator className="bg-sidebar-border" />
      <div className="p-3 shrink-0">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-sidebar-accent/50",
                collapsed && "justify-center",
              )}
            >
              <Avatar className="size-8">
                <AvatarImage src={userAvatarUrl} alt={userName} />
                <AvatarFallback className="bg-primary-light text-white text-xs">
                  {userInitials}
                </AvatarFallback>
              </Avatar>
              {!collapsed && (
                <>
                  <div className="flex-1 text-left min-w-0">
                    <p className="text-sm text-sidebar-foreground truncate">{userName}</p>
                    <p className="text-xs text-sidebar-muted truncate">{userEmail}</p>
                  </div>
                  <ChevronDown className="size-3.5 text-sidebar-muted shrink-0" />
                </>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align={collapsed ? "center" : "end"} side="top" className="w-56">
            <DropdownMenuItem asChild>
              <Link href="/settings/profile">
                <User className="size-4" />
                Profile
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/settings">
                <Settings className="size-4" />
                Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <a href="/auth/logout" className="text-danger">
                <LogOut className="size-4" />
                Log out
              </a>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </>
  );
}

// ─── Breadcrumbs ──────────────────────────────────────────────────────────────

function Breadcrumbs({ matterContext }: { matterContext: ReturnType<typeof parseMatterContext> }) {
  if (!matterContext) return null;

  const crumbs: { label: string; href?: string }[] = [
    { label: "Matters", href: "/matters" },
  ];

  // Matter name — use "Matter" as fallback since we don't have the title here
  crumbs.push({
    label: "Matter",
    href: `/matters/${matterContext.matterId}`,
  });

  if (matterContext.subPage) {
    const label = PAGE_LABELS[matterContext.subPage] ?? matterContext.subPage;
    crumbs.push({ label });
  }

  return (
    <nav className="flex items-center gap-1.5 text-sm" aria-label="Breadcrumb">
      {crumbs.map((crumb, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span className="text-muted-foreground/50">/</span>}
          {crumb.href && i < crumbs.length - 1 ? (
            <Link
              href={crumb.href}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {crumb.label}
            </Link>
          ) : (
            <span className="text-foreground font-medium">{crumb.label}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}

// ─── App Shell ────────────────────────────────────────────────────────────────

interface AppShellProps {
  children: React.ReactNode;
  firmName?: string;
  userName?: string;
  userEmail?: string;
  userAvatarUrl?: string;
}

export function AppShell({
  children,
  firmName = "Smith & Associates",
  userName = "Jane Smith",
  userEmail = "jane@smith-law.com",
  userAvatarUrl,
}: AppShellProps) {
  const pathname = usePathname();
  const matterContext = parseMatterContext(pathname);

  // Desktop collapsed state
  const [collapsed, setCollapsed] = useState(false);
  // Mobile sheet state
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile nav on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Keyboard shortcut: Cmd+K placeholder event
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <TooltipProvider delayDuration={0}>
      <div className="flex h-screen overflow-hidden">
        {/* Desktop sidebar */}
        <aside
          className={cn(
            "hidden md:flex flex-col bg-sidebar-background text-sidebar-foreground transition-all duration-200 ease-out shrink-0 print:hidden",
            collapsed ? "w-[72px]" : "w-[260px]",
          )}
        >
          <SidebarContent
            collapsed={collapsed}
            pathname={pathname}
            matterContext={matterContext}
            firmName={firmName}
            userName={userName}
            userEmail={userEmail}
            userAvatarUrl={userAvatarUrl}
          />

          {/* Collapse toggle */}
          <Separator className="bg-sidebar-border" />
          <button
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="flex items-center justify-center py-3 text-sidebar-muted hover:text-sidebar-foreground transition-colors shrink-0"
          >
            {collapsed ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
          </button>
        </aside>

        {/* Mobile sidebar (sheet) */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetContent side="left" className="w-[280px] p-0 bg-sidebar-background text-sidebar-foreground border-r-0">
            <SidebarContent
              collapsed={false}
              pathname={pathname}
              matterContext={matterContext}
              firmName={firmName}
              userName={userName}
              userEmail={userEmail}
              userAvatarUrl={userAvatarUrl}
              onNavClick={() => setMobileOpen(false)}
            />
          </SheetContent>
        </Sheet>

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden min-w-0">
          {/* Top bar */}
          <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4 sm:px-6 print:hidden">
            <div className="flex items-center gap-3">
              {/* Mobile hamburger */}
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden size-8"
                onClick={() => setMobileOpen(true)}
                aria-label="Open menu"
              >
                <Menu className="size-5" />
              </Button>

              {/* Breadcrumbs */}
              <Breadcrumbs matterContext={matterContext} />
            </div>

            {/* Right side: Cmd+K hint */}
            <button
              type="button"
              onClick={() => {
                window.dispatchEvent(new CustomEvent("open-command-palette"));
              }}
              className="hidden sm:flex items-center gap-2 rounded-md border border-border bg-surface-elevated/50 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors"
            >
              <Search className="size-3.5" />
              <span>Search...</span>
              <kbd className="ml-2 rounded bg-surface-elevated px-1.5 py-0.5 text-[10px] font-mono border border-border">
                ⌘K
              </kbd>
            </button>
          </header>

          {/* Page content with fade-in */}
          <main className="flex-1 overflow-y-auto bg-background">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8 animate-in fade-in duration-200">
              {children}
            </div>
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
