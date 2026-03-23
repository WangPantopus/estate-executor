"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  FileText,
  MessageSquare,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usePortalContext } from "../_hooks/use-portal-context";
import { useState } from "react";

// ─── Nav configuration ────────────────────────────────────────────────────────

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const portalNavItems: NavItem[] = [
  { label: "Overview", href: "", icon: Home },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Messages", href: "/messages", icon: MessageSquare },
];

// ─── Portal Shell ─────────────────────────────────────────────────────────────

export function PortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { matterTitle, userName, firmLogoUrl, firmName, isLoading } =
    usePortalContext();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const userInitials = userName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  // Extract matterId from pathname: /portal/{matterId}/...
  const matterMatch = pathname.match(/^\/portal\/([^/]+)/);
  const basePath = matterMatch ? `/portal/${matterMatch[1]}` : "/portal";

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Top navigation bar */}
      <header className="sticky top-0 z-40 border-b border-border bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <div className="flex h-16 items-center justify-between">
            {/* Left: Logo + estate title */}
            <div className="flex items-center gap-3 min-w-0">
              {firmLogoUrl ? (
                <img
                  src={firmLogoUrl}
                  alt={firmName}
                  className="h-8 w-auto shrink-0"
                />
              ) : (
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground shrink-0">
                  <span className="text-xs font-semibold">
                    {firmName.slice(0, 2).toUpperCase()}
                  </span>
                </div>
              )}
              {!isLoading && (
                <h1 className="text-sm font-medium text-foreground truncate hidden sm:block">
                  {matterTitle}
                </h1>
              )}
            </div>

            {/* Center: Navigation (desktop) */}
            <nav className="hidden sm:flex items-center gap-1">
              {portalNavItems.map((item) => {
                const fullHref =
                  item.href === ""
                    ? basePath
                    : `${basePath}${item.href}`;
                const isActive =
                  item.href === ""
                    ? pathname === basePath
                    : pathname.startsWith(fullHref);

                return (
                  <Link
                    key={item.href || "__overview"}
                    href={fullHref}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-accent text-foreground font-medium"
                        : "text-muted-foreground hover:text-foreground hover:bg-accent/50",
                    )}
                  >
                    <item.icon className="size-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Right: User avatar + mobile menu toggle */}
            <div className="flex items-center gap-2">
              {/* Mobile menu button */}
              <Button
                variant="ghost"
                size="icon"
                className="sm:hidden size-9"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                aria-label="Toggle menu"
              >
                {mobileMenuOpen ? (
                  <X className="size-5" />
                ) : (
                  <Menu className="size-5" />
                )}
              </Button>

              {/* User dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-2 rounded-full transition-colors hover:bg-accent/50 p-1 pr-2">
                    <Avatar className="size-8">
                      <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                        {userInitials}
                      </AvatarFallback>
                    </Avatar>
                    <span className="hidden sm:block text-sm text-foreground">
                      {userName}
                    </span>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem asChild>
                    <a href="/auth/logout" className="text-danger">
                      <LogOut className="size-4" />
                      Sign out
                    </a>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        {/* Mobile navigation menu */}
        {mobileMenuOpen && (
          <div className="sm:hidden border-t border-border bg-surface px-4 pb-3 pt-2">
            <nav className="flex flex-col gap-1">
              {portalNavItems.map((item) => {
                const fullHref =
                  item.href === ""
                    ? basePath
                    : `${basePath}${item.href}`;
                const isActive =
                  item.href === ""
                    ? pathname === basePath
                    : pathname.startsWith(fullHref);

                return (
                  <Link
                    key={item.href || "__overview"}
                    href={fullHref}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors",
                      isActive
                        ? "bg-accent text-foreground font-medium"
                        : "text-muted-foreground hover:text-foreground hover:bg-accent/50",
                    )}
                  >
                    <item.icon className="size-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        )}
      </header>

      {/* Mobile estate title (below header) */}
      {!isLoading && (
        <div className="sm:hidden px-4 py-2 border-b border-border bg-surface">
          <p className="text-sm font-medium text-foreground truncate">
            {matterTitle}
          </p>
        </div>
      )}

      {/* Page content */}
      <main className="flex-1">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-6 sm:py-10 animate-in fade-in duration-200">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-surface py-6">
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <p className="text-center text-xs text-muted-foreground">
            Powered by Estate Executor OS
          </p>
        </div>
      </footer>
    </div>
  );
}
