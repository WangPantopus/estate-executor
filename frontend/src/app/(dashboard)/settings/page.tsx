"use client";

import { useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Loader2,
  UserPlus,
  Trash2,
  Building2,
  Users,
  CreditCard,
  Puzzle,
  ExternalLink,
  AlertTriangle,
  CheckCircle2,
  ArrowUpRight,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import {
  useCurrentUser,
  useFirm,
  useUpdateFirm,
  useFirmMembers,
  useInviteFirmMember,
  useUpdateFirmMember,
  useRemoveFirmMember,
  useBillingOverview,
  useBillingInvoices,
  useCreateCheckout,
  useCreatePortalSession,
} from "@/hooks";
import type { FirmRole, TierLimits, Invoice } from "@/lib/types";

// ─── Constants ────────────────────────────────────────────────────────────────

const FIRM_ID = "current";

const FIRM_TYPE_LABELS: Record<string, string> = {
  law_firm: "Law Firm",
  ria: "RIA",
  trust_company: "Trust Company",
  family_office: "Family Office",
  other: "Other",
};

const ROLE_LABELS: Record<string, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
};

const ROLE_VARIANTS: Record<string, "default" | "info" | "muted"> = {
  owner: "default",
  admin: "info",
  member: "muted",
};

const TIER_DETAILS: Record<string, { name: string; price: string; matters: string; users: string }> = {
  starter: { name: "Starter", price: "$49/mo", matters: "10", users: "2" },
  professional: { name: "Professional", price: "$149/mo", matters: "50", users: "5" },
  growth: { name: "Growth", price: "$349/mo", matters: "200", users: "15" },
  enterprise: { name: "Enterprise", price: "Custom", matters: "Unlimited", users: "Unlimited" },
};

// ─── Invite Schema ────────────────────────────────────────────────────────────

const inviteSchema = z.object({
  email: z.string().email("Valid email required"),
  full_name: z.string().min(1, "Name required"),
  firm_role: z.enum(["admin", "member"] as const),
});

type InviteFormData = z.infer<typeof inviteSchema>;

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: firm, isLoading: firmLoading } = useFirm(FIRM_ID);
  const { data: membersData, isLoading: membersLoading } = useFirmMembers(FIRM_ID);
  const updateFirm = useUpdateFirm(FIRM_ID);
  const updateMember = useUpdateFirmMember(FIRM_ID);
  const removeMember = useRemoveFirmMember(FIRM_ID);

  const [inviteOpen, setInviteOpen] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState("");

  const members = membersData?.data ?? [];

  // Determine current user's role
  const currentMembership = user?.firm_memberships?.[0];
  const isOwner = currentMembership?.firm_role === "owner";
  const isAdmin = isOwner || currentMembership?.firm_role === "admin";

  if (userLoading || firmLoading) {
    return <LoadingState variant="detail" />;
  }

  const tier = firm?.subscription_tier ?? "starter";
  const tierInfo = TIER_DETAILS[tier] ?? TIER_DETAILS.starter;

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" />

      <Tabs defaultValue="general">
        <TabsList>
          <TabsTrigger value="general" className="gap-1.5">
            <Building2 className="size-3.5" />
            General
          </TabsTrigger>
          <TabsTrigger value="team" className="gap-1.5">
            <Users className="size-3.5" />
            Team
          </TabsTrigger>
          <TabsTrigger value="billing" className="gap-1.5">
            <CreditCard className="size-3.5" />
            Billing
          </TabsTrigger>
          <TabsTrigger value="integrations" className="gap-1.5" disabled>
            <Puzzle className="size-3.5" />
            Integrations
          </TabsTrigger>
        </TabsList>

        {/* ─── General Tab ────────────────────────────────────────────────── */}
        <TabsContent value="general">
          <Card>
            <CardContent className="p-6 space-y-6">
              {/* Firm name */}
              <div>
                <Label>Firm Name</Label>
                {editingName ? (
                  <div className="flex items-center gap-2 mt-1">
                    <Input
                      value={nameValue}
                      onChange={(e) => setNameValue(e.target.value)}
                      className="max-w-sm"
                    />
                    <Button
                      size="sm"
                      onClick={() => {
                        if (nameValue.trim()) {
                          updateFirm.mutate(
                            { name: nameValue.trim() },
                            { onSuccess: () => setEditingName(false) },
                          );
                        }
                      }}
                      disabled={updateFirm.isPending}
                    >
                      {updateFirm.isPending ? <Loader2 className="size-4 animate-spin" /> : "Save"}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditingName(false)}>
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 mt-1">
                    <p className="text-sm text-foreground">{firm?.name ?? "—"}</p>
                    {isAdmin && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setNameValue(firm?.name ?? "");
                          setEditingName(true);
                        }}
                      >
                        Edit
                      </Button>
                    )}
                  </div>
                )}
              </div>

              <Separator />

              {/* Firm type */}
              <div>
                <Label>Firm Type</Label>
                <p className="text-sm text-foreground mt-1">
                  {firm ? FIRM_TYPE_LABELS[firm.type] ?? firm.type : "—"}
                </p>
              </div>

              <Separator />

              {/* Slug */}
              <div>
                <Label>Firm Slug</Label>
                <p className="text-sm text-muted-foreground font-mono mt-1">
                  {firm?.slug ?? "—"}
                </p>
              </div>

              <Separator />

              {/* Logo placeholder */}
              <div>
                <Label>Logo</Label>
                <p className="text-xs text-muted-foreground mt-1">
                  Logo upload available on Enterprise plan.
                </p>
                {tier === "enterprise" ? (
                  <Button variant="outline" size="sm" className="mt-2" disabled>
                    Upload Logo
                  </Button>
                ) : (
                  <Badge variant="muted" className="mt-2">Enterprise only</Badge>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── Team Tab ───────────────────────────────────────────────────── */}
        <TabsContent value="team">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-medium text-foreground">Team Members</h3>
                  <p className="text-xs text-muted-foreground">{members.length} member{members.length !== 1 ? "s" : ""}</p>
                </div>
                {isAdmin && (
                  <Button size="sm" onClick={() => setInviteOpen(true)}>
                    <UserPlus className="size-4 mr-1" />
                    Invite Member
                  </Button>
                )}
              </div>

              {membersLoading ? (
                <LoadingState variant="list" count={3} />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {members.map((member) => (
                      <TableRow key={member.id}>
                        <TableCell className="font-medium">{member.full_name}</TableCell>
                        <TableCell className="text-muted-foreground">{member.email}</TableCell>
                        <TableCell>
                          {isOwner && member.firm_role !== "owner" ? (
                            <Select
                              value={member.firm_role}
                              onValueChange={(val) =>
                                updateMember.mutate({
                                  membershipId: member.id,
                                  data: { firm_role: val as FirmRole },
                                })
                              }
                            >
                              <SelectTrigger className="h-7 w-24 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="admin">Admin</SelectItem>
                                <SelectItem value="member">Member</SelectItem>
                              </SelectContent>
                            </Select>
                          ) : (
                            <Badge variant={ROLE_VARIANTS[member.firm_role] ?? "muted"} className="text-xs">
                              {ROLE_LABELS[member.firm_role] ?? member.firm_role}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {isOwner && member.firm_role !== "owner" && member.user_id !== user?.user_id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-danger hover:text-danger"
                              onClick={() => {
                                if (confirm(`Remove ${member.full_name} from the firm?`)) {
                                  removeMember.mutate(member.id);
                                }
                              }}
                              disabled={removeMember.isPending}
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Invite dialog */}
          <InviteMemberDialog
            open={inviteOpen}
            onOpenChange={setInviteOpen}
            firmId={FIRM_ID}
          />
        </TabsContent>

        {/* ─── Billing Tab ────────────────────────────────────────────────── */}
        <TabsContent value="billing">
          <BillingTabContent firmId={FIRM_ID} isOwner={isOwner} isAdmin={isAdmin} />
        </TabsContent>

        {/* ─── Integrations Tab (disabled) ────────────────────────────────── */}
        <TabsContent value="integrations">
          <Card>
            <CardContent className="p-6 text-center py-12">
              <Puzzle className="size-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">Integrations coming in Phase 4.</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Invite Member Dialog ─────────────────────────────────────────────────────

function InviteMemberDialog({
  open,
  onOpenChange,
  firmId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  firmId: string;
}) {
  const inviteMember = useInviteFirmMember(firmId);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: "", full_name: "", firm_role: "member" },
  });

  const watchRole = watch("firm_role");

  const handleClose = useCallback(() => {
    reset();
    onOpenChange(false);
  }, [reset, onOpenChange]);

  const onSubmit = async (data: InviteFormData) => {
    try {
      await inviteMember.mutateAsync(data);
      handleClose();
    } catch {
      // handled by mutation
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Invite Team Member</DialogTitle>
          <DialogDescription>Add a new member to your firm.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="inv-email">Email <span className="text-danger">*</span></Label>
            <Input id="inv-email" type="email" {...register("email")} className="mt-1" />
            {errors.email && <p className="text-xs text-danger mt-1">{errors.email.message}</p>}
          </div>
          <div>
            <Label htmlFor="inv-name">Full Name <span className="text-danger">*</span></Label>
            <Input id="inv-name" {...register("full_name")} className="mt-1" />
            {errors.full_name && <p className="text-xs text-danger mt-1">{errors.full_name.message}</p>}
          </div>
          <div>
            <Label>Role</Label>
            <Select
              value={watchRole}
              onValueChange={(v) => setValue("firm_role", v as "admin" | "member")}
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="member">Member</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {inviteMember.error && (
            <p className="text-sm text-danger">Failed to send invitation.</p>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={handleClose}>Cancel</Button>
            <Button type="submit" disabled={inviteMember.isPending}>
              {inviteMember.isPending && <Loader2 className="size-4 mr-1 animate-spin" />}
              Send Invite
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Billing Tab Content ─────────────────────────────────────────────────────

const PLAN_ORDER = ["starter", "professional", "growth", "enterprise"] as const;

const STATUS_CONFIG: Record<string, { label: string; variant: "default" | "info" | "muted"; icon: typeof CheckCircle2 }> = {
  active: { label: "Active", variant: "default", icon: CheckCircle2 },
  trialing: { label: "Trial", variant: "info", icon: CheckCircle2 },
  past_due: { label: "Past Due", variant: "muted", icon: AlertTriangle },
  canceled: { label: "Canceled", variant: "muted", icon: AlertTriangle },
  unpaid: { label: "Unpaid", variant: "muted", icon: AlertTriangle },
  incomplete: { label: "Incomplete", variant: "muted", icon: AlertTriangle },
  paused: { label: "Paused", variant: "muted", icon: AlertTriangle },
};

function formatCents(cents: number): string {
  return `$${(cents / 100).toFixed(0)}`;
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function BillingTabContent({
  firmId,
  isOwner,
  isAdmin,
}: {
  firmId: string;
  isOwner: boolean;
  isAdmin: boolean;
}) {
  const { data: billing, isLoading: billingLoading, isError: billingError } = useBillingOverview(firmId);
  const { data: invoiceData, isLoading: invoicesLoading } = useBillingInvoices(firmId);
  const createCheckout = useCreateCheckout(firmId);
  const createPortal = useCreatePortalSession(firmId);

  const [selectedInterval, setSelectedInterval] = useState<"month" | "year">("month");
  const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false);

  // Reset interval when dialog opens
  const openUpgradeDialog = useCallback(() => {
    setSelectedInterval("month");
    setUpgradeDialogOpen(true);
  }, []);

  if (billingLoading) {
    return <LoadingState variant="detail" />;
  }

  if (billingError) {
    return (
      <Card>
        <CardContent className="p-6 text-center py-12">
          <AlertTriangle className="size-8 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            Unable to load billing information. Please try again later.
          </p>
        </CardContent>
      </Card>
    );
  }

  const sub = billing?.subscription;
  const usage = billing?.usage;
  const tierLimits = billing?.tier_limits ?? {};
  const currentTier = sub?.tier ?? "starter";
  const currentStatus = sub?.status ?? "active";
  const statusCfg = STATUS_CONFIG[currentStatus] ?? STATUS_CONFIG.active;
  const currentLimits = tierLimits[currentTier];

  const handleManageBilling = async () => {
    try {
      const result = await createPortal.mutateAsync({});
      window.location.href = result.portal_url;
    } catch {
      // handled by mutation
    }
  };

  const handleUpgrade = async (tier: string) => {
    try {
      const result = await createCheckout.mutateAsync({
        tier,
        billing_interval: selectedInterval,
      });
      window.location.href = result.checkout_url;
    } catch {
      // handled by mutation
    }
  };

  const invoices = invoiceData?.invoices ?? [];

  return (
    <div className="space-y-4">
      {/* Payment failure warning */}
      {currentStatus === "past_due" && (
        <Card className="border-amber-500/50 bg-amber-50 dark:bg-amber-950/20">
          <CardContent className="p-4 flex items-start gap-3">
            <AlertTriangle className="size-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                Payment failed
              </p>
              <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
                {sub?.last_payment_error ?? "Your last payment could not be processed."}
                {sub?.grace_period_end && (
                  <> Access will be restricted after {formatDate(sub.grace_period_end)}.</>
                )}
              </p>
              {isAdmin && (
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-2"
                  onClick={handleManageBilling}
                  disabled={createPortal.isPending}
                >
                  {createPortal.isPending && <Loader2 className="size-3 mr-1 animate-spin" />}
                  Update Payment Method
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current plan */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-foreground">Current Plan</h3>
            <Badge variant={statusCfg.variant} className="text-xs gap-1">
              <statusCfg.icon className="size-3" />
              {statusCfg.label}
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-xl font-semibold text-foreground">
                {TIER_DETAILS[currentTier]?.name ?? currentTier}
              </p>
              <p className="text-sm text-muted-foreground">
                {sub?.billing_interval === "year" ? (
                  <>
                    {currentLimits ? formatCents(currentLimits.annual_price_cents) : "—"}/year
                    <span className="text-xs ml-1 text-green-600">(annual discount)</span>
                  </>
                ) : (
                  <>{currentLimits ? formatCents(currentLimits.monthly_price_cents) : "—"}/month</>
                )}
              </p>
              {sub?.cancel_at_period_end && (
                <p className="text-xs text-amber-600 mt-1">
                  Cancels at end of period ({formatDate(sub.current_period_end)})
                </p>
              )}
              {sub?.current_period_end && !sub.cancel_at_period_end && (
                <p className="text-xs text-muted-foreground mt-1">
                  Renews {formatDate(sub.current_period_end)}
                </p>
              )}
            </div>
            <div className="flex gap-2">
              {isAdmin && currentTier !== "enterprise" && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={openUpgradeDialog}
                >
                  <ArrowUpRight className="size-3.5 mr-1" />
                  Upgrade
                </Button>
              )}
              {isAdmin && sub?.stripe_subscription_id && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleManageBilling}
                  disabled={createPortal.isPending}
                >
                  {createPortal.isPending ? (
                    <Loader2 className="size-3.5 mr-1 animate-spin" />
                  ) : (
                    <ExternalLink className="size-3.5 mr-1" />
                  )}
                  Manage
                </Button>
              )}
            </div>
          </div>

          <Separator className="my-4" />

          {/* Usage meters */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-muted-foreground">Active Matters</p>
                <p className="text-xs font-medium">
                  {usage?.matter_count ?? 0} /{" "}
                  {usage && usage.matter_limit >= 999999 ? "Unlimited" : (usage?.matter_limit ?? "—")}
                </p>
              </div>
              <Progress
                aria-label={`${usage?.matter_count ?? 0} of ${usage?.matter_limit ?? 0} matters used`}
                value={
                  usage && usage.matter_limit > 0 && usage.matter_limit < 999999
                    ? Math.min((usage.matter_count / usage.matter_limit) * 100, 100)
                    : 0
                }
                className="h-2"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-muted-foreground">Team Members</p>
                <p className="text-xs font-medium">
                  {usage?.user_count ?? 0} /{" "}
                  {usage && usage.user_limit >= 999999 ? "Unlimited" : (usage?.user_limit ?? "—")}
                </p>
              </div>
              <Progress
                aria-label={`${usage?.user_count ?? 0} of ${usage?.user_limit ?? 0} team members used`}
                value={
                  usage && usage.user_limit > 0 && usage.user_limit < 999999
                    ? Math.min((usage.user_count / usage.user_limit) * 100, 100)
                    : 0
                }
                className="h-2"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Billing history */}
      <Card>
        <CardContent className="p-6">
          <h3 className="text-sm font-medium text-foreground mb-4">Billing History</h3>
          {invoicesLoading ? (
            <LoadingState variant="list" count={3} />
          ) : invoices.length === 0 ? (
            <p className="text-sm text-muted-foreground">No invoices yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((inv: Invoice) => (
                  <TableRow key={inv.id}>
                    <TableCell className="text-sm">
                      {formatDate(inv.created)}
                    </TableCell>
                    <TableCell className="text-sm font-medium">
                      {formatCents(inv.amount_paid || inv.amount_due)}{" "}
                      <span className="text-muted-foreground uppercase text-xs">
                        {inv.currency}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={inv.status === "paid" ? "default" : "muted"}
                        className="text-xs"
                      >
                        {inv.status ?? "—"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {inv.invoice_pdf && (
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                        >
                          <a href={inv.invoice_pdf} target="_blank" rel="noopener noreferrer" aria-label="Download PDF">
                            <Download className="size-3.5" aria-hidden="true" />
                          </a>
                        </Button>
                      )}
                      {inv.invoice_url && (
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                        >
                          <a href={inv.invoice_url} target="_blank" rel="noopener noreferrer" aria-label="View invoice">
                            <ExternalLink className="size-3.5" aria-hidden="true" />
                          </a>
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Upgrade dialog */}
      <Dialog open={upgradeDialogOpen} onOpenChange={setUpgradeDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Upgrade Plan</DialogTitle>
            <DialogDescription>
              Choose a plan that fits your firm. Annual billing saves ~17%.
            </DialogDescription>
          </DialogHeader>

          {/* Interval toggle */}
          <div className="flex items-center justify-center gap-3 py-2">
            <Button
              variant={selectedInterval === "month" ? "default" : "ghost"}
              size="sm"
              onClick={() => setSelectedInterval("month")}
            >
              Monthly
            </Button>
            <Button
              variant={selectedInterval === "year" ? "default" : "ghost"}
              size="sm"
              onClick={() => setSelectedInterval("year")}
            >
              Annual
              <Badge variant="info" className="ml-1.5 text-[10px]">Save ~17%</Badge>
            </Button>
          </div>

          {/* Plan cards */}
          <div className="grid grid-cols-3 gap-4">
            {PLAN_ORDER.filter((t) => t !== "enterprise").map((planKey) => {
              const limits = tierLimits[planKey];
              if (!limits) return null;
              const isCurrent = planKey === currentTier;
              const isDowngrade = PLAN_ORDER.indexOf(planKey) <= PLAN_ORDER.indexOf(currentTier as typeof PLAN_ORDER[number]);
              const price =
                selectedInterval === "year"
                  ? limits.annual_price_cents
                  : limits.monthly_price_cents;

              return (
                <Card
                  key={planKey}
                  className={isCurrent ? "border-primary" : ""}
                >
                  <CardContent className="p-4 space-y-3">
                    <div>
                      <p className="font-semibold text-foreground">
                        {TIER_DETAILS[planKey]?.name ?? planKey}
                      </p>
                      <p className="text-2xl font-bold text-foreground mt-1">
                        {formatCents(price)}
                        <span className="text-sm font-normal text-muted-foreground">
                          /{selectedInterval === "year" ? "yr" : "mo"}
                        </span>
                      </p>
                    </div>
                    <Separator />
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li>Up to {limits.max_matters} matters</li>
                      <li>Up to {limits.max_users} team members</li>
                    </ul>
                    <Button
                      className="w-full"
                      size="sm"
                      variant={isCurrent ? "outline" : "default"}
                      disabled={isCurrent || isDowngrade || createCheckout.isPending}
                      onClick={() => handleUpgrade(planKey)}
                    >
                      {createCheckout.isPending ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : isCurrent ? (
                        "Current Plan"
                      ) : isDowngrade ? (
                        "Downgrade via Portal"
                      ) : (
                        "Upgrade"
                      )}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {createCheckout.error && (
            <p className="text-sm text-danger text-center">
              Failed to start checkout. Please try again.
            </p>
          )}

          <DialogFooter>
            <Button variant="ghost" onClick={() => setUpgradeDialogOpen(false)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
