"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Plus,
  Search,
  LayoutGrid,
  List,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { LoadingState } from "@/components/layout/LoadingState";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { useMatters } from "@/hooks";
import { ESTATE_TYPE_LABELS, PHASE_LABELS, US_STATES } from "@/lib/constants";
import type { Matter, MatterFilters, MatterStatus } from "@/lib/types";
import { CreateMatterDialog } from "./CreateMatterDialog";

function useDebounce(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function getStateLabel(code: string): string {
  return US_STATES.find((s) => s.value === code)?.label ?? code;
}

// Placeholder firmId — will come from context/auth in production
const FIRM_ID = "current";

export function MattersPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [createOpen, setCreateOpen] = useState(false);
  const [view, setView] = useState<"table" | "cards">("table");

  // Filter state from URL params
  const statusFilter =
    (searchParams.get("status") as MatterStatus) || undefined;
  const phaseFilter = searchParams.get("phase") || undefined;
  const jurisdictionFilter = searchParams.get("jurisdiction") || undefined;
  const [searchInput, setSearchInput] = useState(
    searchParams.get("search") || "",
  );
  const searchQuery = useDebounce(searchInput, 300);
  const page = parseInt(searchParams.get("page") || "1", 10);
  const [sortField, setSortField] = useState<string>("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const filters: MatterFilters = useMemo(
    () => ({
      status: statusFilter,
      search: searchQuery || undefined,
      page,
      per_page: 20,
    }),
    [statusFilter, searchQuery, page],
  );

  const { data, isLoading, error } = useMatters(FIRM_ID, filters);

  const updateFilter = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      if (key !== "page") params.delete("page");
      router.push(`/matters?${params.toString()}`);
    },
    [searchParams, router],
  );

  const toggleSort = (field: string) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  // Client-side sort + jurisdiction/phase filtering
  const matters = useMemo(() => {
    let list = data?.data ?? [];
    if (phaseFilter) {
      list = list.filter((m) => m.phase === phaseFilter);
    }
    if (jurisdictionFilter) {
      list = list.filter((m) => m.jurisdiction_state === jurisdictionFilter);
    }
    return [...list].sort((a, b) => {
      const aVal = (a as unknown as Record<string, unknown>)[sortField];
      const bVal = (b as unknown as Record<string, unknown>)[sortField];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data?.data, phaseFilter, jurisdictionFilter, sortField, sortDir]);

  const meta = data?.meta;
  const hasFilters =
    statusFilter || searchQuery || phaseFilter || jurisdictionFilter;

  const SortHeader = ({
    field,
    children,
  }: {
    field: string;
    children: React.ReactNode;
  }) => (
    <button
      onClick={() => toggleSort(field)}
      className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
    >
      {children}
      <ArrowUpDown className="size-3 opacity-40" />
    </button>
  );

  return (
    <>
      <PageHeader
        title="Matters"
        subtitle="Manage all active and archived estate matters"
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus /> New Matter
          </Button>
        }
      />

      {/* Filter bar */}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search matters..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select
            value={statusFilter ?? "all"}
            onValueChange={(v) =>
              updateFilter("status", v === "all" ? null : v)
            }
          >
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="on_hold">On Hold</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={phaseFilter ?? "all"}
            onValueChange={(v) =>
              updateFilter("phase", v === "all" ? null : v)
            }
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Phase" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All phases</SelectItem>
              <SelectItem value="immediate">Immediate</SelectItem>
              <SelectItem value="administration">Administration</SelectItem>
              <SelectItem value="distribution">Distribution</SelectItem>
              <SelectItem value="closing">Closing</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={jurisdictionFilter ?? "all"}
            onValueChange={(v) =>
              updateFilter("jurisdiction", v === "all" ? null : v)
            }
          >
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Jurisdiction" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All jurisdictions</SelectItem>
              {US_STATES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant={view === "table" ? "secondary" : "ghost"}
            size="icon"
            onClick={() => setView("table")}
          >
            <List className="size-4" />
          </Button>
          <Button
            variant={view === "cards" ? "secondary" : "ghost"}
            size="icon"
            onClick={() => setView("cards")}
          >
            <LayoutGrid className="size-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="mt-6">
        {isLoading ? (
          view === "table" ? (
            <LoadingState variant="table" count={5} />
          ) : (
            <LoadingState variant="cards" count={6} />
          )
        ) : error ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-danger">
              Failed to load matters. Please try again.
            </CardContent>
          </Card>
        ) : matters.length === 0 ? (
          hasFilters ? (
            <EmptyState
              title="No matters match your filters"
              description="Try adjusting your search or filter criteria."
              action={
                <Button
                  variant="outline"
                  onClick={() => router.push("/matters")}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              title="No matters yet"
              description="Create your first matter to get started with estate administration."
              action={
                <Button onClick={() => setCreateOpen(true)}>
                  <Plus /> Create Matter
                </Button>
              }
            />
          )
        ) : view === "table" ? (
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>
                    <SortHeader field="title">Matter</SortHeader>
                  </TableHead>
                  <TableHead>
                    <SortHeader field="decedent_name">Decedent</SortHeader>
                  </TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Jurisdiction</TableHead>
                  <TableHead>Phase</TableHead>
                  <TableHead>Progress</TableHead>
                  <TableHead>
                    <SortHeader field="created_at">Created</SortHeader>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {matters.map((matter) => (
                  <MatterTableRow key={matter.id} matter={matter} />
                ))}
              </TableBody>
            </Table>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {matters.map((matter) => (
              <MatterCard key={matter.id} matter={matter} />
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {meta && meta.total_pages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing page {meta.page} of {meta.total_pages} ({meta.total}{" "}
            matters)
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={meta.page <= 1}
              onClick={() => updateFilter("page", String(meta.page - 1))}
            >
              <ChevronLeft className="size-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={meta.page >= meta.total_pages}
              onClick={() => updateFilter("page", String(meta.page + 1))}
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Create dialog */}
      <CreateMatterDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        firmId={FIRM_ID}
      />
    </>
  );
}

// ─── Table row ───────────────────────────────────────────────────────────────

function MatterTableRow({ matter }: { matter: Matter }) {
  const router = useRouter();
  const estateLabel =
    ESTATE_TYPE_LABELS[matter.estate_type]?.label ?? matter.estate_type;

  return (
    <TableRow
      className="cursor-pointer"
      onClick={() => router.push(`/matters/${matter.id}`)}
    >
      <TableCell>
        <Link
          href={`/matters/${matter.id}`}
          className="font-medium text-foreground hover:text-primary transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          {matter.title}
        </Link>
      </TableCell>
      <TableCell className="text-muted-foreground">
        {matter.decedent_name}
      </TableCell>
      <TableCell>
        <span className="text-sm">{estateLabel}</span>
      </TableCell>
      <TableCell>{getStateLabel(matter.jurisdiction_state)}</TableCell>
      <TableCell>
        <Badge variant="muted">
          {PHASE_LABELS[matter.phase] ?? matter.phase}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2 min-w-[100px]">
          <Progress value={0} className="h-1.5 flex-1" />
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            —
          </span>
        </div>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        {formatDate(matter.created_at)}
      </TableCell>
    </TableRow>
  );
}

// ─── Card view ───────────────────────────────────────────────────────────────

function MatterCard({ matter }: { matter: Matter }) {
  const estateLabel =
    ESTATE_TYPE_LABELS[matter.estate_type]?.label ?? matter.estate_type;

  return (
    <Link href={`/matters/${matter.id}`}>
      <Card className="transition-shadow duration-200 hover:shadow-md">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="min-w-0 flex-1">
              <CardTitle className="truncate">{matter.title}</CardTitle>
              <CardDescription className="mt-1">
                {matter.decedent_name} ·{" "}
                {getStateLabel(matter.jurisdiction_state)}
              </CardDescription>
            </div>
            <StatusBadge status={matter.status} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 text-sm">
            <div>
              <p className="text-muted-foreground text-xs">Type</p>
              <p className="font-medium">{estateLabel}</p>
            </div>
            <Separator orientation="vertical" className="h-8" />
            <div>
              <p className="text-muted-foreground text-xs">Est. Value</p>
              <p className="font-medium">
                {matter.estimated_value
                  ? `$${matter.estimated_value.toLocaleString()}`
                  : "—"}
              </p>
            </div>
          </div>
        </CardContent>
        <CardFooter className="gap-2">
          <Badge variant="muted">
            {PHASE_LABELS[matter.phase] ?? matter.phase}
          </Badge>
          <span className="text-xs text-muted-foreground ml-auto">
            {formatDate(matter.created_at)}
          </span>
        </CardFooter>
      </Card>
    </Link>
  );
}
