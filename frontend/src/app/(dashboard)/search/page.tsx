"use client";

import { useState, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Search,
  Briefcase,
  CheckSquare,
  DollarSign,
  FileText,
  MessageSquare,
  Loader2,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useSearch, useCurrentUser } from "@/hooks";
import type { SearchEntityType, SearchResult } from "@/lib/types";

const ENTITY_TYPE_CONFIG: Record<
  SearchEntityType,
  { label: string; icon: React.ReactNode; color: string }
> = {
  matter: {
    label: "Matters",
    icon: <Briefcase className="size-4" />,
    color: "bg-blue-100 text-blue-700",
  },
  task: {
    label: "Tasks",
    icon: <CheckSquare className="size-4" />,
    color: "bg-green-100 text-green-700",
  },
  asset: {
    label: "Assets",
    icon: <DollarSign className="size-4" />,
    color: "bg-amber-100 text-amber-700",
  },
  document: {
    label: "Documents",
    icon: <FileText className="size-4" />,
    color: "bg-purple-100 text-purple-700",
  },
  communication: {
    label: "Communications",
    icon: <MessageSquare className="size-4" />,
    color: "bg-pink-100 text-pink-700",
  },
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

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [activeFilter, setActiveFilter] = useState<SearchEntityType | null>(null);
  const { data: user } = useCurrentUser();
  const firmId = user?.firm_id ?? "";

  const { data, isLoading, isFetching } = useSearch(firmId, query, {
    entityTypes: activeFilter ?? undefined,
    enabled: !!firmId,
  });

  const grouped = useMemo(() => {
    if (!data?.results) return {};
    const groups: Record<string, SearchResult[]> = {};
    for (const r of data.results) {
      (groups[r.entity_type] ??= []).push(r);
    }
    return groups;
  }, [data]);

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-semibold mb-6">Search</h1>

      {/* Search input */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search matters, tasks, assets, documents, messages..."
          className="pl-10 h-11"
          autoFocus
        />
        {isFetching && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 size-4 animate-spin text-muted-foreground" />
        )}
      </div>

      {/* Entity type filter chips */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          type="button"
          onClick={() => setActiveFilter(null)}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            activeFilter === null
              ? "bg-primary text-primary-foreground"
              : "bg-surface-elevated text-muted-foreground hover:text-foreground"
          }`}
        >
          All {data?.total ? `(${data.total})` : ""}
        </button>
        {(Object.entries(data?.groups ?? {}) as [SearchEntityType, number][]).map(
          ([type, count]) => {
            const config = ENTITY_TYPE_CONFIG[type];
            if (!config) return null;
            return (
              <button
                key={type}
                type="button"
                onClick={() => setActiveFilter(activeFilter === type ? null : type)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  activeFilter === type
                    ? "bg-primary text-primary-foreground"
                    : "bg-surface-elevated text-muted-foreground hover:text-foreground"
                }`}
              >
                {config.icon}
                {config.label} ({count})
              </button>
            );
          },
        )}
      </div>

      {/* Results */}
      {query.length < 2 ? (
        <p className="text-sm text-muted-foreground text-center py-12">
          Type at least 2 characters to search.
        </p>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-12 gap-2 text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          <span className="text-sm">Searching...</span>
        </div>
      ) : data?.total === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-12">
          No results found for &ldquo;{query}&rdquo;.
        </p>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([entityType, results]) => {
            const config = ENTITY_TYPE_CONFIG[entityType as SearchEntityType];
            if (!config) return null;
            return (
              <div key={entityType}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={`p-1 rounded ${config.color}`}>{config.icon}</span>
                  <h2 className="text-sm font-semibold">{config.label}</h2>
                  <Badge variant="secondary" className="text-xs">
                    {results.length}
                  </Badge>
                </div>
                <div className="space-y-1">
                  {results.map((result) => (
                    <button
                      key={`${result.entity_type}-${result.entity_id}`}
                      type="button"
                      onClick={() => router.push(getResultUrl(result))}
                      className="w-full text-left rounded-lg border border-border px-4 py-3 hover:bg-surface-elevated transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-foreground truncate">
                            {result.title}
                          </p>
                          {result.subtitle && (
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {result.subtitle}
                            </p>
                          )}
                          <p
                            className="text-xs text-muted-foreground mt-1 line-clamp-2 [&_mark]:bg-yellow-200 [&_mark]:text-foreground [&_mark]:rounded-sm [&_mark]:px-0.5"
                            dangerouslySetInnerHTML={{ __html: result.snippet }}
                          />
                        </div>
                        <Badge variant="outline" className="text-[10px] shrink-0 mt-0.5">
                          {entityType}
                        </Badge>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
