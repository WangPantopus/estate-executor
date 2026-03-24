"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Briefcase,
  Settings,
  User,
  Plus,
  ArrowRight,
  CheckSquare,
  DollarSign,
  FileText,
  MessageSquare,
  Loader2,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog";
import { cn, sanitizeSnippet } from "@/lib/utils";
import { useSearch, useCurrentUser } from "@/hooks";
import type { SearchEntityType, SearchResult } from "@/lib/types";

// ─── Quick Actions ────────────────────────────────────────────────────────────

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  action: () => void;
  category: "action" | "navigation";
}

const ENTITY_ICONS: Record<SearchEntityType, React.ReactNode> = {
  matter: <Briefcase className="size-4" />,
  task: <CheckSquare className="size-4" />,
  asset: <DollarSign className="size-4" />,
  document: <FileText className="size-4" />,
  communication: <MessageSquare className="size-4" />,
};

function getResultUrl(result: SearchResult): string {
  const base = `/matters/${result.matter_id}`;
  switch (result.entity_type) {
    case "matter":
      return base;
    case "task":
      return `${base}/tasks`;
    case "asset":
      return `${base}/assets`;
    case "document":
      return `${base}/documents`;
    case "communication":
      return `${base}/communications`;
    default:
      return base;
  }
}

// ─── Component ────────────────────────────────────────────────────────────────

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const { data: user } = useCurrentUser();
  const firmId = user?.firm_id ?? "";

  // Live search — only fires when query is 2+ chars
  const { data: searchData, isFetching } = useSearch(firmId, query, {
    limit: 5,
    enabled: open && !!firmId,
  });

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
      setQuery(""); // eslint-disable-line react-hooks/set-state-in-effect -- reset form on open
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

  // When there's a search query, show search results; otherwise show commands
  const isSearching = query.length >= 2;
  const searchResults = searchData?.results ?? [];

  const filtered = isSearching
    ? [] // hide commands when searching
    : query
      ? commands.filter(
          (c) =>
            c.label.toLowerCase().includes(query.toLowerCase()) ||
            c.description?.toLowerCase().includes(query.toLowerCase()),
        )
      : commands;

  // +1 for the "View all results" button when searching
  const totalItems = isSearching
    ? searchResults.length + (searchResults.length > 0 ? 1 : 0)
    : filtered.length;

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, totalItems - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (isSearching) {
        if (searchResults[selectedIndex]) {
          router.push(getResultUrl(searchResults[selectedIndex]));
          setOpen(false);
        } else if (query.length >= 2) {
          // Navigate to full search page
          router.push(`/search?q=${encodeURIComponent(query)}`);
          setOpen(false);
        }
      } else if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
      }
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
          {isFetching && (
            <Loader2 className="size-4 animate-spin text-muted-foreground shrink-0" />
          )}
          <kbd className="rounded bg-surface-elevated px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground border border-border">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[350px] overflow-y-auto py-2">
          {/* Search results section */}
          {isSearching && (
            <>
              {searchResults.length > 0 ? (
                <div>
                  <p className="px-4 py-1 text-xs font-medium text-muted-foreground">
                    Results
                  </p>
                  {searchResults.map((result, idx) => (
                    <button
                      key={`${result.entity_type}-${result.entity_id}`}
                      type="button"
                      onClick={() => {
                        router.push(getResultUrl(result));
                        setOpen(false);
                      }}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={cn(
                        "flex items-center gap-3 w-full px-4 py-2.5 text-sm text-left transition-colors",
                        idx === selectedIndex
                          ? "bg-surface-elevated text-foreground"
                          : "text-muted-foreground hover:bg-surface-elevated/50",
                      )}
                    >
                      <span className="shrink-0">
                        {ENTITY_ICONS[result.entity_type] ?? <Search className="size-4" />}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{result.title}</p>
                        <p
                          className="text-xs text-muted-foreground truncate [&_mark]:bg-yellow-200 [&_mark]:text-foreground [&_mark]:rounded-sm"
                          dangerouslySetInnerHTML={{ __html: sanitizeSnippet(result.snippet) }}
                        />
                      </div>
                      <span className="text-[10px] text-muted-foreground/60 shrink-0">
                        {result.entity_type}
                      </span>
                    </button>
                  ))}
                  {/* "View all results" link */}
                  <button
                    type="button"
                    onClick={() => {
                      router.push(`/search?q=${encodeURIComponent(query)}`);
                      setOpen(false);
                    }}
                    onMouseEnter={() => setSelectedIndex(searchResults.length)}
                    className={cn(
                      "flex items-center gap-3 w-full px-4 py-2.5 text-sm text-left transition-colors",
                      selectedIndex === searchResults.length
                        ? "bg-surface-elevated text-foreground"
                        : "text-muted-foreground hover:bg-surface-elevated/50",
                    )}
                  >
                    <Search className="size-4 shrink-0" />
                    <span className="font-medium">View all results for &ldquo;{query}&rdquo;</span>
                    <ArrowRight className="size-3.5 text-muted-foreground/50 ml-auto" />
                  </button>
                </div>
              ) : isFetching ? (
                <div className="flex items-center justify-center gap-2 py-6 text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" />
                  <span className="text-sm">Searching...</span>
                </div>
              ) : (
                <p className="px-4 py-6 text-sm text-muted-foreground text-center">
                  No results found for &ldquo;{query}&rdquo;.
                </p>
              )}
            </>
          )}

          {/* Commands section (shown when not searching) */}
          {!isSearching && (
            <>
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
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
