"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  Settings,
  ChevronLeft,
  ChevronRight,
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const mainNavItems: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Matters", href: "/matters", icon: Briefcase },
  { label: "Settings", href: "/settings", icon: Settings },
];

const matterNavItems: NavItem[] = [
  { label: "Tasks", href: "/tasks", icon: ListTodo },
  { label: "Assets", href: "/assets", icon: Landmark },
  { label: "Entities", href: "/entities", icon: Building2 },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Deadlines", href: "/deadlines", icon: Calendar },
  { label: "Communications", href: "/communications", icon: MessageSquare },
  { label: "Activity Log", href: "/activity", icon: Activity },
];

interface AppShellProps {
  children: React.ReactNode;
  firmName?: string;
  userName?: string;
  userEmail?: string;
  userAvatarUrl?: string;
  matterId?: string;
  matterTitle?: string;
  breadcrumbs?: { label: string; href?: string }[];
}

export function AppShell({
  children,
  firmName = "Smith & Associates",
  userName = "Jane Smith",
  userEmail = "jane@smith-law.com",
  userAvatarUrl,
  matterId,
  matterTitle,
  breadcrumbs,
}: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  const userInitials = userName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <TooltipProvider delayDuration={0}>
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <aside
          className={cn(
            "flex flex-col bg-sidebar-background text-sidebar-foreground transition-all duration-200 ease-out",
            collapsed ? "w-[72px]" : "w-[280px]"
          )}
        >
          {/* Logo */}
          <div className="flex h-16 items-center px-5">
            {collapsed ? (
              <span className="text-lg font-semibold text-white">EE</span>
            ) : (
              <span className="text-base font-medium tracking-tight text-white">
                Estate Executor<span className="text-gold"> OS</span>
              </span>
            )}
          </div>

          {/* Firm name */}
          {!collapsed && (
            <div className="px-5 pb-4">
              <p className="text-xs text-sidebar-muted truncate">{firmName}</p>
            </div>
          )}

          <Separator className="bg-sidebar-border" />

          {/* Navigation */}
          <ScrollArea className="flex-1 py-4">
            <nav className="space-y-1 px-3">
              {mainNavItems.map((item) => {
                const isActive =
                  pathname === item.href ||
                  pathname.startsWith(item.href + "/");

                const link = (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors duration-150",
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                    )}
                  >
                    <item.icon
                      className={cn(
                        "size-[18px] shrink-0",
                        isActive && "text-gold"
                      )}
                    />
                    {!collapsed && <span>{item.label}</span>}
                    {isActive && !collapsed && (
                      <div className="ml-auto h-1.5 w-1.5 rounded-full bg-gold" />
                    )}
                  </Link>
                );

                if (collapsed) {
                  return (
                    <Tooltip key={item.href}>
                      <TooltipTrigger asChild>{link}</TooltipTrigger>
                      <TooltipContent side="right">
                        {item.label}
                      </TooltipContent>
                    </Tooltip>
                  );
                }

                return link;
              })}
            </nav>

            {/* Matter navigation (when inside a matter) */}
            {matterId && (
              <>
                <div className="px-5 pt-6 pb-2">
                  {!collapsed && (
                    <p className="text-[11px] font-medium uppercase tracking-widest text-sidebar-muted">
                      Current Matter
                    </p>
                  )}
                  {!collapsed && matterTitle && (
                    <p className="mt-1 text-sm text-sidebar-foreground truncate">
                      {matterTitle}
                    </p>
                  )}
                </div>
                <nav className="space-y-1 px-3">
                  {matterNavItems.map((item) => {
                    const fullHref = `/matters/${matterId}${item.href}`;
                    const isActive = pathname.startsWith(fullHref);

                    const link = (
                      <Link
                        key={item.href}
                        href={fullHref}
                        className={cn(
                          "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors duration-150",
                          isActive
                            ? "bg-sidebar-accent text-sidebar-accent-foreground"
                            : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                        )}
                      >
                        <item.icon
                          className={cn(
                            "size-[18px] shrink-0",
                            isActive && "text-gold"
                          )}
                        />
                        {!collapsed && <span>{item.label}</span>}
                      </Link>
                    );

                    if (collapsed) {
                      return (
                        <Tooltip key={item.href}>
                          <TooltipTrigger asChild>{link}</TooltipTrigger>
                          <TooltipContent side="right">
                            {item.label}
                          </TooltipContent>
                        </Tooltip>
                      );
                    }

                    return link;
                  })}
                </nav>
              </>
            )}
          </ScrollArea>

          {/* Collapse toggle */}
          <Separator className="bg-sidebar-border" />
          <button
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="flex items-center justify-center py-3 text-sidebar-muted hover:text-sidebar-foreground transition-colors"
          >
            {collapsed ? (
              <ChevronRight className="size-4" />
            ) : (
              <ChevronLeft className="size-4" />
            )}
          </button>

          {/* User section */}
          <Separator className="bg-sidebar-border" />
          <div className="p-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-sidebar-accent/50",
                    collapsed && "justify-center"
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
                        <p className="text-sm text-sidebar-foreground truncate">
                          {userName}
                        </p>
                        <p className="text-xs text-sidebar-muted truncate">
                          {userEmail}
                        </p>
                      </div>
                      <ChevronDown className="size-3.5 text-sidebar-muted shrink-0" />
                    </>
                  )}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align={collapsed ? "center" : "end"}
                side="top"
                className="w-56"
              >
                <DropdownMenuItem>
                  <User className="size-4" />
                  Profile
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Settings className="size-4" />
                  Settings
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
        </aside>

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Top bar */}
          <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
            <div className="flex items-center gap-2 text-sm">
              {breadcrumbs ? (
                <nav className="flex items-center gap-1.5">
                  {breadcrumbs.map((crumb, i) => (
                    <React.Fragment key={i}>
                      {i > 0 && (
                        <span className="text-muted-foreground">/</span>
                      )}
                      {crumb.href ? (
                        <Link
                          href={crumb.href}
                          className="text-muted-foreground hover:text-foreground transition-colors"
                        >
                          {crumb.label}
                        </Link>
                      ) : (
                        <span className="text-foreground font-medium">
                          {crumb.label}
                        </span>
                      )}
                    </React.Fragment>
                  ))}
                </nav>
              ) : matterTitle ? (
                <nav className="flex items-center gap-1.5">
                  <Link
                    href="/matters"
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Matters
                  </Link>
                  <span className="text-muted-foreground">/</span>
                  <span className="text-foreground font-medium">
                    {matterTitle}
                  </span>
                </nav>
              ) : null}
            </div>
          </header>

          {/* Page content */}
          <main className="flex-1 overflow-y-auto bg-background">
            <div className="mx-auto max-w-7xl px-6 py-8">{children}</div>
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
