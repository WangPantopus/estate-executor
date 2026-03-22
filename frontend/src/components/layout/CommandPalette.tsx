"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Briefcase,
  Settings,
  User,
  Plus,
  ArrowRight,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

// ─── Quick Actions ────────────────────────────────────────────────────────────

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  action: () => void;
  category: "action" | "navigation";
}

// ─── Component ────────────────────────────────────────────────────────────────

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut: Cmd+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);

    // Also listen for custom event from search bar
    const customHandler = () => setOpen(true);
    window.addEventListener("open-command-palette", customHandler);

    return () => {
      window.removeEventListener("keydown", handler);
      window.removeEventListener("open-command-palette", customHandler);
    };
  }, []);

  // Reset on open
  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  const commands: CommandItem[] = [
    {
      id: "new-matter",
      label: "New Matter",
      description: "Create a new estate matter",
      icon: <Plus className="size-4" />,
      action: () => { router.push("/matters"); setOpen(false); },
      category: "action",
    },
    {
      id: "nav-matters",
      label: "Go to Matters",
      icon: <Briefcase className="size-4" />,
      action: () => { router.push("/matters"); setOpen(false); },
      category: "navigation",
    },
    {
      id: "nav-settings",
      label: "Go to Settings",
      icon: <Settings className="size-4" />,
      action: () => { router.push("/settings"); setOpen(false); },
      category: "navigation",
    },
    {
      id: "nav-profile",
      label: "Go to Profile",
      icon: <User className="size-4" />,
      action: () => { router.push("/settings/profile"); setOpen(false); },
      category: "navigation",
    },
  ];

  const filtered = query
    ? commands.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          c.description?.toLowerCase().includes(query.toLowerCase()),
      )
    : commands;

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && filtered[selectedIndex]) {
      e.preventDefault();
      filtered[selectedIndex].action();
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-md p-0 gap-0 overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Search className="size-4 text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search or type a command..."
            className="flex-1 h-12 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          <kbd className="rounded bg-surface-elevated px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground border border-border">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[300px] overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <p className="px-4 py-6 text-sm text-muted-foreground text-center">
              No results found.
            </p>
          ) : (
            <>
              {/* Actions */}
              {filtered.some((c) => c.category === "action") && (
                <div>
                  <p className="px-4 py-1 text-xs font-medium text-muted-foreground">Actions</p>
                  {filtered
                    .filter((c) => c.category === "action")
                    .map((cmd, idx) => {
                      const globalIdx = filtered.indexOf(cmd);
                      return (
                        <button
                          key={cmd.id}
                          type="button"
                          onClick={cmd.action}
                          onMouseEnter={() => setSelectedIndex(globalIdx)}
                          className={cn(
                            "flex items-center gap-3 w-full px-4 py-2.5 text-sm text-left transition-colors",
                            globalIdx === selectedIndex
                              ? "bg-surface-elevated text-foreground"
                              : "text-muted-foreground hover:bg-surface-elevated/50",
                          )}
                        >
                          <span className="shrink-0">{cmd.icon}</span>
                          <div className="flex-1">
                            <p className="font-medium">{cmd.label}</p>
                            {cmd.description && (
                              <p className="text-xs text-muted-foreground">{cmd.description}</p>
                            )}
                          </div>
                          <ArrowRight className="size-3.5 text-muted-foreground/50" />
                        </button>
                      );
                    })}
                </div>
              )}

              {/* Navigation */}
              {filtered.some((c) => c.category === "navigation") && (
                <div>
                  <p className="px-4 py-1 text-xs font-medium text-muted-foreground mt-1">Navigation</p>
                  {filtered
                    .filter((c) => c.category === "navigation")
                    .map((cmd) => {
                      const globalIdx = filtered.indexOf(cmd);
                      return (
                        <button
                          key={cmd.id}
                          type="button"
                          onClick={cmd.action}
                          onMouseEnter={() => setSelectedIndex(globalIdx)}
                          className={cn(
                            "flex items-center gap-3 w-full px-4 py-2.5 text-sm text-left transition-colors",
                            globalIdx === selectedIndex
                              ? "bg-surface-elevated text-foreground"
                              : "text-muted-foreground hover:bg-surface-elevated/50",
                          )}
                        >
                          <span className="shrink-0">{cmd.icon}</span>
                          <span className="font-medium">{cmd.label}</span>
                          <ArrowRight className="size-3.5 text-muted-foreground/50 ml-auto" />
                        </button>
                      );
                    })}
                </div>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
