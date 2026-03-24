"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, User, ChevronDown, Home, FileText, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SocketProvider } from "@/components/providers/SocketProvider";
import { ToastProvider } from "@/components/layout/Toaster";

// ─── Portal nav items ─────────────────────────────────────────────────────────

interface PortalNavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

function getPortalNavItems(matterId: string): PortalNavItem[] {
  return [
    { label: "Overview", href: `/portal/${matterId}`, icon: Home },
    { label: "Documents", href: `/portal/${matterId}/documents`, icon: FileText },
    { label: "Messages", href: `/portal/${matterId}/messages`, icon: MessageSquare },
  ];
}

function extractMatterId(pathname: string): string | null {
  const match = pathname.match(/^\/portal\/([^/]+)/);
  return match ? match[1] : null;
}

// ─── Portal Layout ────────────────────────────────────────────────────────────

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const matterId = extractMatterId(pathname);

  // Placeholder user info — in production, comes from useCurrentUser
  const userName = "Beneficiary";
  const userInitials = "B";

  const navItems = matterId ? getPortalNavItems(matterId) : [];

  return (
    <ToastProvider>
      <SocketProvider>
        <div className="flex min-h-screen flex-col bg-background">
          {/* Top navigation bar */}
          <header className="sticky top-0 z-40 border-b border-border/40 bg-white/80 backdrop-blur-md">
            <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 sm:px-6">
              {/* Left: Logo / estate title */}
              <div className="flex items-center gap-4">
                <Link href={matterId ? `/portal/${matterId}` : "/portal"} className="flex items-center gap-2">
                  <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-white text-xs font-semibold">
                    EE
                  </div>
                  <span className="hidden sm:inline text-sm font-medium text-foreground/80">
                    Estate Executor
                  </span>
                </Link>

                {/* Nav items */}
                {matterId && (
                  <nav className="ml-4 hidden sm:flex items-center gap-1">
                    {navItems.map((item) => {
                      const isActive =
                        item.href === `/portal/${matterId}`
                          ? pathname === item.href
                          : pathname.startsWith(item.href);
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={cn(
                            "flex items-center gap-2 rounded-full px-4 py-2 text-sm transition-colors",
                            isActive
                              ? "bg-primary/10 text-primary font-medium"
                              : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                          )}
                        >
                          <item.icon className="size-4" />
                          {item.label}
                        </Link>
                      );
                    })}
                  </nav>
                )}
              </div>

              {/* Right: User menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-2 rounded-full px-2 py-1.5 transition-colors hover:bg-muted/50">
                    <Avatar className="size-8">
                      <AvatarImage alt={userName} />
                      <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                        {userInitials}
                      </AvatarFallback>
                    </Avatar>
                    <span className="hidden sm:inline text-sm text-foreground">{userName}</span>
                    <ChevronDown className="hidden sm:inline size-3.5 text-muted-foreground" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem asChild>
                    <Link href="/settings/profile">
                      <User className="size-4" />
                      Profile
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

            {/* Mobile nav */}
            {matterId && (
              <div className="sm:hidden border-t border-border/30">
                <nav className="flex items-center gap-1 px-4 py-2 overflow-x-auto">
                  {navItems.map((item) => {
                    const isActive =
                      item.href === `/portal/${matterId}`
                        ? pathname === item.href
                        : pathname.startsWith(item.href);
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                          "flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1.5 text-xs transition-colors",
                          isActive
                            ? "bg-primary/10 text-primary font-medium"
                            : "text-muted-foreground hover:text-foreground",
                        )}
                      >
                        <item.icon className="size-3.5" />
                        {item.label}
                      </Link>
                    );
                  })}
                </nav>
              </div>
            )}
          </header>

          {/* Page content — generous white space for calm feel */}
          <main className="flex-1">
            <div className="mx-auto max-w-5xl px-4 sm:px-6 py-8 sm:py-12 animate-in fade-in duration-300">
              {children}
            </div>
          </main>

          {/* Footer */}
          <footer className="border-t border-border/30 bg-muted/20 py-6">
            <div className="mx-auto max-w-5xl px-4 sm:px-6">
              <p className="text-center text-xs text-muted-foreground">
                Powered by Estate Executor OS
              </p>
            </div>
          </footer>
        </div>
      </SocketProvider>
    </ToastProvider>
  );
}
