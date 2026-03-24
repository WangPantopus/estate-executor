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
  RefreshCw,
  Shield,
  Plug,
  Unplug,
  Clock,
  FolderSync,
  UserCheck,
  Key,
  Webhook,
  Copy,
  Send,
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
  useSSOConfig,
  useEnableSSO,
  useDisableSSO,
  useAPIKeys,
  useCreateAPIKey,
  useRevokeAPIKey,
  useDeleteAPIKey,
  useWebhooks,
  useCreateWebhook,
  useDeleteWebhook,
  useTestWebhook,
  useBillingOverview,
  useBillingInvoices,
  useCreateCheckout,
  useCreatePortalSession,
  useClioConnection,
  useConnectClio,
  useDisconnectClio,
  useSyncClio,
  useDocuSignConnection,
  useConnectDocuSign,
  useDisconnectDocuSign,
  useQuickBooksConnection,
  useConnectQuickBooks,
  useDisconnectQuickBooks,
  useSyncQuickBooks,
  useMyPrivacyRequests,
  usePrivacyQueue,
  useCreatePrivacyRequest,
  useReviewPrivacyRequest,
  useDownloadDataExport,
} from "@/hooks";
import type { FirmRole, TierLimits, Invoice, SyncRequest, PrivacyRequest } from "@/lib/types";

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
          <TabsTrigger value="integrations" className="gap-1.5">
            <Puzzle className="size-3.5" />
            Integrations
          </TabsTrigger>
          {tier === "enterprise" && (
            <TabsTrigger value="developer" className="gap-1.5">
              <Key className="size-3.5" />
              Developer
            </TabsTrigger>
          )}
          <TabsTrigger value="privacy" className="gap-1.5">
            <Shield className="size-3.5" />
            Privacy
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

              {/* Branding — available on Growth/Enterprise */}
              <div>
                <Label>Branding</Label>
                {tier === "growth" || tier === "enterprise" ? (
                  <div className="mt-2 space-y-3">
                    <div>
                      <p className="text-xs text-muted-foreground">
                        Logo and colors are configured in the Branding section below.
                      </p>
                    </div>
                    {firm?.white_label?.logo_url && (
                      <div className="flex items-center gap-3">
                        <img
                          src={firm.white_label.logo_url}
                          alt="Firm logo"
                          className="h-10 w-auto max-w-[160px] object-contain rounded border border-border p-1"
                        />
                        <p className="text-xs text-muted-foreground">Current logo</p>
                      </div>
                    )}
                    {firm?.white_label?.primary_color && (
                      <div className="flex items-center gap-2">
                        <div
                          className="size-6 rounded border border-border"
                          style={{ backgroundColor: firm.white_label.primary_color }}
                        />
                        <p className="text-xs text-muted-foreground font-mono">
                          {firm.white_label.primary_color}
                        </p>
                      </div>
                    )}
                    {firm?.white_label?.custom_domain && (
                      <div>
                        <p className="text-xs text-muted-foreground">
                          Custom domain:{" "}
                          <span className="font-mono text-foreground">
                            {firm.white_label.custom_domain}
                          </span>
                          {firm.white_label.custom_domain_verified ? (
                            <Badge variant="default" className="ml-2 text-[10px]">Verified</Badge>
                          ) : (
                            <Badge variant="muted" className="ml-2 text-[10px]">Pending</Badge>
                          )}
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="mt-1">
                    <p className="text-xs text-muted-foreground">
                      White-label branding available on Growth and Enterprise plans.
                    </p>
                    <Badge variant="muted" className="mt-2">Growth+ only</Badge>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Enterprise SSO */}
          {tier === "enterprise" && <SSOConfigCard firmId={FIRM_ID} isOwner={isOwner} />}
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

        {/* ─── Integrations Tab ─────────────────────────────────────────── */}
        <TabsContent value="integrations">
          <IntegrationsTabContent firmId={FIRM_ID} isAdmin={isAdmin} />
        </TabsContent>

        {/* ─── Developer Tab ──────────────────────────────────────────────── */}
        {tier === "enterprise" && (
          <TabsContent value="developer" className="space-y-4">
            <APIKeysCard firmId={FIRM_ID} isAdmin={isAdmin} />
            <WebhooksCard firmId={FIRM_ID} isAdmin={isAdmin} />
          </TabsContent>
        )}

        {/* ─── Privacy Tab ────────────────────────────────────────────────── */}
        <TabsContent value="privacy" className="space-y-4">
          <PrivacyTabContent firmId={FIRM_ID} isAdmin={isAdmin} />
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

// ─── Integrations Tab Content ────────────────────────────────────────────────

function IntegrationsTabContent({
  firmId,
  isAdmin,
}: {
  firmId: string;
  isAdmin: boolean;
}) {
  const { data: clio, isLoading: clioLoading } = useClioConnection(firmId);
  const connectClio = useConnectClio(firmId);
  const disconnectClio = useDisconnectClio(firmId);
  const syncClio = useSyncClio(firmId);

  const { data: docusign, isLoading: dsLoading } = useDocuSignConnection(firmId);
  const connectDocuSign = useConnectDocuSign(firmId);
  const disconnectDocuSign = useDisconnectDocuSign(firmId);

  const { data: qbo, isLoading: qboLoading } = useQuickBooksConnection(firmId);
  const connectQBO = useConnectQuickBooks(firmId);
  const disconnectQBO = useDisconnectQuickBooks(firmId);
  const syncQBO = useSyncQuickBooks(firmId);
  const [qboSyncing, setQboSyncing] = useState<string | null>(null);

  const [syncingResource, setSyncingResource] = useState<string | null>(null);

  const isConnected = clio?.status === "connected";

  const handleConnect = async () => {
    try {
      const result = await connectClio.mutateAsync();
      window.location.href = result.authorize_url;
    } catch {
      // handled by mutation
    }
  };

  const handleDisconnect = async () => {
    if (!confirm("Disconnect Clio? Sync mappings will be preserved for reconnection.")) return;
    try {
      await disconnectClio.mutateAsync();
    } catch {
      // handled by mutation
    }
  };

  const handleSync = async (resource: SyncRequest["resource"]) => {
    setSyncingResource(resource);
    try {
      await syncClio.mutateAsync({ resource });
    } catch {
      // handled by mutation
    } finally {
      setSyncingResource(null);
    }
  };

  if (clioLoading) {
    return <LoadingState variant="detail" />;
  }

  return (
    <div className="space-y-4">
      {/* Clio Integration Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-lg bg-blue-100 dark:bg-blue-950 flex items-center justify-center">
                <span className="text-blue-700 dark:text-blue-300 font-bold text-sm">CL</span>
              </div>
              <div>
                <h3 className="text-sm font-medium text-foreground">Clio Manage</h3>
                <p className="text-xs text-muted-foreground">
                  Legal practice management — sync matters, time entries, and contacts
                </p>
              </div>
            </div>
            <Badge
              variant={isConnected ? "default" : "muted"}
              className="text-xs gap-1"
            >
              {isConnected ? (
                <><CheckCircle2 className="size-3" aria-hidden="true" /> Connected</>
              ) : (
                <><Unplug className="size-3" aria-hidden="true" /> Not Connected</>
              )}
            </Badge>
          </div>

          {isConnected && clio?.external_account_name && (
            <p className="text-xs text-muted-foreground mb-4">
              Connected to: <span className="font-medium text-foreground">{clio.external_account_name}</span>
              {clio.last_sync_at && (
                <> &middot; Last synced {formatDate(clio.last_sync_at)}</>
              )}
            </p>
          )}

          <div className="flex gap-2">
            {isAdmin && !isConnected && (
              <Button
                size="sm"
                onClick={handleConnect}
                disabled={connectClio.isPending}
              >
                {connectClio.isPending ? (
                  <Loader2 className="size-3.5 mr-1 animate-spin" />
                ) : (
                  <Plug className="size-3.5 mr-1" />
                )}
                Connect Clio
              </Button>
            )}
            {isAdmin && isConnected && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleDisconnect}
                  disabled={disconnectClio.isPending}
                >
                  {disconnectClio.isPending ? (
                    <Loader2 className="size-3.5 mr-1 animate-spin" />
                  ) : (
                    <Unplug className="size-3.5 mr-1" />
                  )}
                  Disconnect
                </Button>
              </>
            )}
          </div>

          {connectClio.error && (
            <p className="text-xs text-danger mt-2">Failed to initiate Clio connection.</p>
          )}
          {disconnectClio.error && (
            <p className="text-xs text-danger mt-2">Failed to disconnect Clio.</p>
          )}
        </CardContent>
      </Card>

      {/* Sync Controls — only shown when connected */}
      {isConnected && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-sm font-medium text-foreground mb-4">Sync Controls</h3>

            {clio?.last_sync_error && (
              <div className="flex items-start gap-2 mb-4 p-3 rounded-md bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800">
                <AlertTriangle className="size-4 text-red-600 shrink-0 mt-0.5" />
                <p className="text-xs text-red-700 dark:text-red-300">{clio.last_sync_error}</p>
              </div>
            )}

            <div className="space-y-3">
              {/* Matters sync */}
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <FolderSync className="size-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-foreground">Matters</p>
                    <p className="text-xs text-muted-foreground">Bidirectional sync with Clio matters</p>
                  </div>
                </div>
                {isAdmin && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSync("matters")}
                    disabled={syncingResource !== null}
                    aria-label="Sync matters with Clio"
                  >
                    {syncingResource === "matters" ? (
                      <Loader2 className="size-3.5 mr-1 animate-spin" />
                    ) : (
                      <RefreshCw className="size-3.5 mr-1" aria-hidden="true" />
                    )}
                    Sync
                  </Button>
                )}
              </div>

              <Separator />

              {/* Time entries sync */}
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <Clock className="size-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-foreground">Time Entries</p>
                    <p className="text-xs text-muted-foreground">Push time entries to Clio activities</p>
                  </div>
                </div>
                {isAdmin && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSync("time_entries")}
                    disabled={syncingResource !== null}
                    aria-label="Sync time entries to Clio"
                  >
                    {syncingResource === "time_entries" ? (
                      <Loader2 className="size-3.5 mr-1 animate-spin" />
                    ) : (
                      <RefreshCw className="size-3.5 mr-1" aria-hidden="true" />
                    )}
                    Sync
                  </Button>
                )}
              </div>

              <Separator />

              {/* Contacts sync */}
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <UserCheck className="size-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-foreground">Contacts</p>
                    <p className="text-xs text-muted-foreground">Sync contacts with Clio stakeholders</p>
                  </div>
                </div>
                {isAdmin && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSync("contacts")}
                    disabled={syncingResource !== null}
                    aria-label="Sync contacts with Clio"
                  >
                    {syncingResource === "contacts" ? (
                      <Loader2 className="size-3.5 mr-1 animate-spin" />
                    ) : (
                      <RefreshCw className="size-3.5 mr-1" aria-hidden="true" />
                    )}
                    Sync
                  </Button>
                )}
              </div>
            </div>

            {syncClio.data && !syncClio.isPending && (
              <div className="mt-4 p-3 rounded-md bg-muted/50 text-xs">
                <p className="font-medium text-foreground mb-1">
                  Last sync: {syncClio.data.resource}
                </p>
                <p className="text-muted-foreground">
                  Created: {syncClio.data.created} &middot;
                  Updated: {syncClio.data.updated} &middot;
                  Skipped: {syncClio.data.skipped}
                  {syncClio.data.errors.length > 0 && (
                    <span className="text-danger"> &middot; Errors: {syncClio.data.errors.length}</span>
                  )}
                </p>
              </div>
            )}

            {syncClio.error && (
              <p className="text-xs text-danger mt-2">Sync failed. Please try again.</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* DocuSign Integration Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-lg bg-yellow-100 dark:bg-yellow-950 flex items-center justify-center">
                <span className="text-yellow-700 dark:text-yellow-300 font-bold text-sm">DS</span>
              </div>
              <div>
                <h3 className="text-sm font-medium text-foreground">DocuSign</h3>
                <p className="text-xs text-muted-foreground">
                  E-signatures — send documents for signing, track status, receive signed copies
                </p>
              </div>
            </div>
            <Badge
              variant={docusign?.status === "connected" ? "default" : "muted"}
              className="text-xs gap-1"
            >
              {docusign?.status === "connected" ? (
                <><CheckCircle2 className="size-3" aria-hidden="true" /> Connected</>
              ) : (
                <><Unplug className="size-3" aria-hidden="true" /> Not Connected</>
              )}
            </Badge>
          </div>

          {docusign?.status === "connected" && docusign.external_account_name && (
            <p className="text-xs text-muted-foreground mb-4">
              Connected to: <span className="font-medium text-foreground">{docusign.external_account_name}</span>
            </p>
          )}

          <div className="flex gap-2">
            {isAdmin && docusign?.status !== "connected" && (
              <Button
                size="sm"
                onClick={async () => {
                  try {
                    const r = await connectDocuSign.mutateAsync();
                    window.location.href = r.authorize_url;
                  } catch { /* handled */ }
                }}
                disabled={connectDocuSign.isPending}
              >
                {connectDocuSign.isPending ? (
                  <Loader2 className="size-3.5 mr-1 animate-spin" />
                ) : (
                  <Plug className="size-3.5 mr-1" />
                )}
                Connect DocuSign
              </Button>
            )}
            {isAdmin && docusign?.status === "connected" && (
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  if (!confirm("Disconnect DocuSign?")) return;
                  try {
                    await disconnectDocuSign.mutateAsync();
                  } catch { /* handled */ }
                }}
                disabled={disconnectDocuSign.isPending}
              >
                {disconnectDocuSign.isPending ? (
                  <Loader2 className="size-3.5 mr-1 animate-spin" />
                ) : (
                  <Unplug className="size-3.5 mr-1" />
                )}
                Disconnect
              </Button>
            )}
          </div>

          {connectDocuSign.error && (
            <p className="text-xs text-danger mt-2">Failed to initiate DocuSign connection.</p>
          )}
          {disconnectDocuSign.error && (
            <p className="text-xs text-danger mt-2">Failed to disconnect DocuSign.</p>
          )}

          {docusign?.status === "connected" && (
            <p className="text-xs text-muted-foreground mt-3">
              Send documents for signature from any matter&apos;s Documents tab.
            </p>
          )}
        </CardContent>
      </Card>

      {/* QuickBooks Integration Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-lg bg-green-100 dark:bg-green-950 flex items-center justify-center">
                <span className="text-green-700 dark:text-green-300 font-bold text-sm">QB</span>
              </div>
              <div>
                <h3 className="text-sm font-medium text-foreground">QuickBooks Online</h3>
                <p className="text-xs text-muted-foreground">
                  Accounting — push distributions, transactions, pull bank balances
                </p>
              </div>
            </div>
            <Badge
              variant={qbo?.status === "connected" ? "default" : "muted"}
              className="text-xs gap-1"
            >
              {qbo?.status === "connected" ? (
                <><CheckCircle2 className="size-3" aria-hidden="true" /> Connected</>
              ) : (
                <><Unplug className="size-3" aria-hidden="true" /> Not Connected</>
              )}
            </Badge>
          </div>

          {qbo?.status === "connected" && qbo.external_account_name && (
            <p className="text-xs text-muted-foreground mb-4">
              Connected to: <span className="font-medium text-foreground">{qbo.external_account_name}</span>
              {qbo.last_sync_at && <> &middot; Last synced {formatDate(qbo.last_sync_at)}</>}
            </p>
          )}

          <div className="flex gap-2">
            {isAdmin && qbo?.status !== "connected" && (
              <Button
                size="sm"
                onClick={async () => {
                  try {
                    const r = await connectQBO.mutateAsync();
                    window.location.href = r.authorize_url;
                  } catch { /* handled */ }
                }}
                disabled={connectQBO.isPending}
              >
                {connectQBO.isPending ? (
                  <Loader2 className="size-3.5 mr-1 animate-spin" />
                ) : (
                  <Plug className="size-3.5 mr-1" />
                )}
                Connect QuickBooks
              </Button>
            )}
            {isAdmin && qbo?.status === "connected" && (
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  if (!confirm("Disconnect QuickBooks?")) return;
                  try { await disconnectQBO.mutateAsync(); } catch { /* handled */ }
                }}
                disabled={disconnectQBO.isPending}
              >
                {disconnectQBO.isPending ? (
                  <Loader2 className="size-3.5 mr-1 animate-spin" />
                ) : (
                  <Unplug className="size-3.5 mr-1" />
                )}
                Disconnect
              </Button>
            )}
          </div>

          {connectQBO.error && (
            <p className="text-xs text-danger mt-2">Failed to initiate QuickBooks connection.</p>
          )}
          {disconnectQBO.error && (
            <p className="text-xs text-danger mt-2">Failed to disconnect QuickBooks.</p>
          )}
        </CardContent>
      </Card>

      {/* QuickBooks Sync Controls */}
      {qbo?.status === "connected" && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-sm font-medium text-foreground mb-4">QuickBooks Sync</h3>
            <div className="space-y-3">
              {([
                { key: "distributions", label: "Distributions", desc: "Push distributions as journal entries" },
                { key: "transactions", label: "Transactions", desc: "Push estate bank transactions" },
                { key: "account_balances", label: "Account Balances", desc: "Pull bank balances for reconciliation" },
              ] as const).map((item) => (
                <div key={item.key}>
                  <div className="flex items-center justify-between py-2">
                    <div>
                      <p className="text-sm text-foreground">{item.label}</p>
                      <p className="text-xs text-muted-foreground">{item.desc}</p>
                    </div>
                    {isAdmin && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={qboSyncing !== null}
                        aria-label={`Sync ${item.label.toLowerCase()} with QuickBooks`}
                        onClick={async () => {
                          setQboSyncing(item.key);
                          try {
                            await syncQBO.mutateAsync({ resource: item.key });
                          } catch { /* handled */ } finally {
                            setQboSyncing(null);
                          }
                        }}
                      >
                        {qboSyncing === item.key ? (
                          <Loader2 className="size-3.5 mr-1 animate-spin" />
                        ) : (
                          <RefreshCw className="size-3.5 mr-1" aria-hidden="true" />
                        )}
                        Sync
                      </Button>
                    )}
                  </div>
                  {item.key !== "account_balances" && <Separator />}
                </div>
              ))}
            </div>

            {syncQBO.data && !syncQBO.isPending && (
              <div className="mt-4 p-3 rounded-md bg-muted/50 text-xs">
                <p className="font-medium text-foreground mb-1">
                  Last sync: {syncQBO.data.resource}
                </p>
                <p className="text-muted-foreground">
                  Created: {syncQBO.data.created} &middot;
                  Updated: {syncQBO.data.updated} &middot;
                  Skipped: {syncQBO.data.skipped}
                  {syncQBO.data.errors.length > 0 && (
                    <span className="text-danger"> &middot; Errors: {syncQBO.data.errors.length}</span>
                  )}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Xero coming soon */}
      <Card>
        <CardContent className="p-6">
          <h3 className="text-sm font-medium text-foreground mb-3">Coming Soon</h3>
          <div className="p-3 rounded-lg border border-dashed border-border text-center max-w-xs">
            <p className="text-sm font-medium text-muted-foreground">Xero</p>
            <p className="text-xs text-muted-foreground/60">Accounting sync</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── SSO Config Card ─────────────────────────────────────────────────────────

function SSOConfigCard({ firmId, isOwner }: { firmId: string; isOwner: boolean }) {
  const { data: sso, isLoading } = useSSOConfig(firmId);
  const enableSSO = useEnableSSO(firmId);
  const disableSSO = useDisableSSO(firmId);

  if (isLoading) return null;

  const isConfigured = sso !== null && sso !== undefined;
  const isEnabled = isConfigured && sso?.enabled;

  return (
    <Card className="mt-4">
      <CardContent className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-foreground">Enterprise SSO</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {isConfigured
                ? `${(sso?.protocol ?? "").toUpperCase()} — ${sso?.auth0_connection_name ?? "pending"}`
                : "SAML or OIDC single sign-on for your organization"}
            </p>
          </div>
          <Badge variant={isEnabled ? "default" : "muted"} className="text-xs">
            {isEnabled ? "Enabled" : isConfigured ? "Configured" : "Not Configured"}
          </Badge>
        </div>

        {isConfigured && (
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Protocol</span>
              <span className="font-medium text-foreground">{sso?.protocol?.toUpperCase()}</span>
            </div>
            {sso?.saml_entity_id && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Entity ID</span>
                <span className="font-mono text-foreground truncate max-w-[200px]">{sso.saml_entity_id}</span>
              </div>
            )}
            {sso?.oidc_discovery_url && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Discovery URL</span>
                <span className="font-mono text-foreground truncate max-w-[200px]">{sso.oidc_discovery_url}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Enforce SSO-only</span>
              <Badge variant={sso?.enforce_sso ? "default" : "muted"} className="text-[10px]">
                {sso?.enforce_sso ? "Yes" : "No"}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Auto-provision users</span>
              <Badge variant={sso?.auto_provision ? "default" : "muted"} className="text-[10px]">
                {sso?.auto_provision ? "Yes" : "No"}
              </Badge>
            </div>
            {sso?.allowed_domains && sso.allowed_domains.length > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Allowed domains</span>
                <span className="font-mono text-foreground">{sso.allowed_domains.join(", ")}</span>
              </div>
            )}
            {sso?.last_login_at && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Last SSO login</span>
                <span className="text-foreground">{formatDate(sso.last_login_at)}</span>
              </div>
            )}
          </div>
        )}

        {isOwner && isConfigured && (
          <div className="flex gap-2 pt-2">
            {isEnabled ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => disableSSO.mutate()}
                disabled={disableSSO.isPending}
              >
                {disableSSO.isPending && <Loader2 className="size-3.5 mr-1 animate-spin" />}
                Disable SSO
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={() => enableSSO.mutate()}
                disabled={enableSSO.isPending}
              >
                {enableSSO.isPending && <Loader2 className="size-3.5 mr-1 animate-spin" />}
                Enable SSO
              </Button>
            )}
          </div>
        )}

        {!isConfigured && isOwner && (
          <p className="text-xs text-muted-foreground">
            Contact support to configure SAML or OIDC single sign-on for your organization.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── API Keys Card ───────────────────────────────────────────────────────────

function APIKeysCard({ firmId, isAdmin }: { firmId: string; isAdmin: boolean }) {
  const { data: keys, isLoading } = useAPIKeys(firmId);
  const createKey = useCreateAPIKey(firmId);
  const revokeKey = useRevokeAPIKey(firmId);
  const deleteKey = useDeleteAPIKey(firmId);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [showNewKeyForm, setShowNewKeyForm] = useState(false);
  const [keyName, setKeyName] = useState("");
  const handleCreate = useCallback(async () => {
    if (!keyName.trim()) return;
    const result = await createKey.mutateAsync({ name: keyName.trim() });
    setNewKey(result.raw_key);
    setKeyName("");
    setShowNewKeyForm(false);
  }, [keyName, createKey]);

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text);
  }, []);

  if (isLoading) return null;

  return (
    <Card>
      <CardContent className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-foreground">API Keys</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Manage API keys for programmatic access
            </p>
          </div>
          {isAdmin && (
            <Button size="sm" onClick={() => setShowNewKeyForm(true)}>
              <Key className="size-3.5 mr-1" />
              Create Key
            </Button>
          )}
        </div>

        {newKey && (
          <div className="p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-md space-y-2">
            <p className="text-xs font-medium text-green-800 dark:text-green-200">
              API key created! Copy it now — it won&apos;t be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="text-xs bg-green-100 dark:bg-green-900 px-2 py-1 rounded flex-1 truncate">
                {newKey}
              </code>
              <Button size="sm" variant="outline" onClick={() => { copyToClipboard(newKey); }}>
                <Copy className="size-3" />
              </Button>
            </div>
            <Button size="sm" variant="ghost" onClick={() => setNewKey(null)} className="text-xs">
              Dismiss
            </Button>
          </div>
        )}

        {showNewKeyForm && (
          <div className="flex gap-2">
            <Input
              placeholder="Key name (e.g. Production API)"
              value={keyName}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setKeyName(e.target.value)}
              className="text-sm"
            />
            <Button size="sm" onClick={handleCreate} disabled={createKey.isPending || !keyName.trim()}>
              {createKey.isPending ? <Loader2 className="size-3.5 animate-spin" /> : "Create"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowNewKeyForm(false)}>
              Cancel
            </Button>
          </div>
        )}

        {keys && keys.length > 0 ? (
          <div className="space-y-2">
            {keys.map((k) => (
              <div key={k.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-md">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{k.name}</span>
                    <Badge variant={k.is_active ? "default" : "muted"} className="text-[10px]">
                      {k.is_active ? "Active" : "Revoked"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <code>{k.key_prefix}...</code>
                    <span>{k.total_requests.toLocaleString()} requests</span>
                    <span>{k.rate_limit_per_minute}/min</span>
                    {k.last_used_at && <span>Last used {formatDate(k.last_used_at)}</span>}
                  </div>
                </div>
                {isAdmin && k.is_active && (
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => revokeKey.mutate(k.id)}
                      disabled={revokeKey.isPending}
                    >
                      Revoke
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => deleteKey.mutate(k.id)}
                      disabled={deleteKey.isPending}
                    >
                      <Trash2 className="size-3.5 text-destructive" />
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            No API keys created yet.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Webhooks Card ───────────────────────────────────────────────────────────

function WebhooksCard({ firmId, isAdmin }: { firmId: string; isAdmin: boolean }) {
  const { data: webhooks, isLoading } = useWebhooks(firmId);
  const createWebhook = useCreateWebhook(firmId);
  const deleteWebhook = useDeleteWebhook(firmId);
  const testWebhook = useTestWebhook(firmId);
  const [showForm, setShowForm] = useState(false);
  const [whUrl, setWhUrl] = useState("");
  const [whEvents, setWhEvents] = useState("matter.created,task.updated");
  const [testResult, setTestResult] = useState<{ id: string; success: boolean } | null>(null);

  const handleCreate = useCallback(async () => {
    if (!whUrl.trim()) return;
    await createWebhook.mutateAsync({
      url: whUrl.trim(),
      events: whEvents.split(",").map((e) => e.trim()).filter(Boolean),
    });
    setWhUrl("");
    setWhEvents("matter.created,task.updated");
    setShowForm(false);
  }, [whUrl, whEvents, createWebhook]);

  const handleTest = useCallback(async (webhookId: string) => {
    const result = await testWebhook.mutateAsync(webhookId);
    setTestResult({ id: webhookId, success: result.success });
    setTimeout(() => setTestResult(null), 5000);
  }, [testWebhook]);

  if (isLoading) return null;

  return (
    <Card>
      <CardContent className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-foreground">Webhooks</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Receive HTTP notifications when events occur
            </p>
          </div>
          {isAdmin && (
            <Button size="sm" onClick={() => setShowForm(true)}>
              <Webhook className="size-3.5 mr-1" />
              Add Endpoint
            </Button>
          )}
        </div>

        {showForm && (
          <div className="space-y-2 p-3 border rounded-md">
            <Input
              placeholder="https://your-server.com/webhooks"
              value={whUrl}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setWhUrl(e.target.value)}
              className="text-sm"
            />
            <Input
              placeholder="Events (comma-separated)"
              value={whEvents}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setWhEvents(e.target.value)}
              className="text-sm font-mono text-xs"
            />
            <p className="text-[10px] text-muted-foreground">
              Available: matter.created, matter.updated, task.created, task.updated, task.completed,
              document.uploaded, stakeholder.added, asset.created, distribution.created, deadline.approaching
            </p>
            <div className="flex gap-2">
              <Button size="sm" onClick={handleCreate} disabled={createWebhook.isPending || !whUrl.trim()}>
                {createWebhook.isPending ? <Loader2 className="size-3.5 animate-spin" /> : "Create"}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {webhooks && webhooks.length > 0 ? (
          <div className="space-y-2">
            {webhooks.map((wh) => (
              <div key={wh.id} className="p-3 bg-muted/50 rounded-md space-y-2">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <code className="text-xs truncate max-w-[300px]">{wh.url}</code>
                      <Badge variant={wh.is_active ? "default" : "muted"} className="text-[10px]">
                        {wh.is_active ? "Active" : "Inactive"}
                      </Badge>
                      {wh.failure_count > 0 && (
                        <Badge variant="danger" className="text-[10px]">
                          {wh.failure_count} failures
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                      {wh.events.map((e) => (
                        <span key={e} className="bg-muted px-1.5 py-0.5 rounded">{e}</span>
                      ))}
                    </div>
                  </div>
                  {isAdmin && (
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleTest(wh.id)}
                        disabled={testWebhook.isPending}
                      >
                        <Send className="size-3 mr-1" />
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => deleteWebhook.mutate(wh.id)}
                        disabled={deleteWebhook.isPending}
                      >
                        <Trash2 className="size-3.5 text-destructive" />
                      </Button>
                    </div>
                  )}
                </div>
                {testResult?.id === wh.id && (
                  <div className={`text-xs px-2 py-1 rounded ${testResult.success
                    ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"
                    : "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300"
                  }`}>
                    {testResult.success ? "Test delivery successful" : "Test delivery failed"}
                  </div>
                )}
                {wh.last_triggered_at && (
                  <p className="text-[10px] text-muted-foreground">
                    Last triggered {formatDate(wh.last_triggered_at)}
                  </p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            No webhook endpoints configured.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Privacy Tab Content ─────────────────────────────────────────────────────

function PrivacyTabContent({ firmId, isAdmin }: { firmId: string; isAdmin: boolean }) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const { data: myRequests } = useMyPrivacyRequests(firmId);
  const { data: queue, isLoading: loadingQueue } = usePrivacyQueue(firmId, undefined);
  const createRequest = useCreatePrivacyRequest(firmId);
  const reviewRequest = useReviewPrivacyRequest(firmId);
  const downloadExport = useDownloadDataExport(firmId);

  const handleExport = async () => {
    try {
      const data = await downloadExport.mutateAsync();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `data-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Error handled by mutation
    }
  };

  const handleDeletionRequest = async () => {
    await createRequest.mutateAsync({ request_type: "data_deletion" });
    setShowDeleteConfirm(false);
  };

  const STATUS_COLORS: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    approved: "bg-blue-100 text-blue-700",
    processing: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
  };

  return (
    <>
      {/* Your Data */}
      <Card>
        <CardContent className="p-6 space-y-4">
          <h3 className="text-sm font-semibold">Your Data</h3>
          <p className="text-xs text-muted-foreground">
            Under GDPR and CCPA, you have the right to access, export, and request deletion of your personal data.
          </p>

          <div className="flex flex-wrap gap-3">
            <Button
              variant="outline"
              onClick={handleExport}
              disabled={downloadExport.isPending}
            >
              {downloadExport.isPending ? (
                <Loader2 className="size-4 animate-spin mr-2" />
              ) : (
                <Download className="size-4 mr-2" />
              )}
              Export My Data (JSON)
            </Button>
            <Button
              variant="outline"
              className="text-danger border-danger/30 hover:bg-danger/5"
              onClick={() => setShowDeleteConfirm(true)}
            >
              <Trash2 className="size-4 mr-2" />
              Request Data Deletion
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* My Privacy Requests */}
      {myRequests && myRequests.length > 0 && (
        <Card>
          <CardContent className="p-6 space-y-3">
            <h3 className="text-sm font-semibold">My Requests</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Note</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {myRequests.map((req: PrivacyRequest) => (
                  <TableRow key={req.id}>
                    <TableCell className="text-xs font-medium">
                      {req.request_type === "data_export" ? "Data Export" : "Data Deletion"}
                    </TableCell>
                    <TableCell>
                      <Badge className={`text-[10px] ${STATUS_COLORS[req.status] ?? ""}`}>
                        {req.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(req.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {req.review_note ?? "\u2014"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Admin: Deletion Request Queue */}
      {isAdmin && (
        <Card>
          <CardContent className="p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Deletion Request Queue (Admin)</h3>
              {queue && (
                <Badge variant="secondary" className="text-xs">
                  {queue.total} request{queue.total !== 1 ? "s" : ""}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Review and approve or reject data deletion requests. Approved requests
              anonymize PII while retaining structural data for audit integrity.
            </p>

            {loadingQueue ? (
              <div className="flex items-center gap-2 py-4 text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                <span className="text-xs">Loading...</span>
              </div>
            ) : queue?.data.length === 0 ? (
              <p className="text-xs text-muted-foreground py-4 text-center">
                No pending requests.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {queue?.data.map((req: PrivacyRequest) => (
                    <TableRow key={req.id}>
                      <TableCell className="text-xs">
                        <p className="font-medium">{req.user_name ?? "Unknown"}</p>
                        <p className="text-muted-foreground">{req.user_email}</p>
                      </TableCell>
                      <TableCell className="text-xs">
                        {req.request_type === "data_export" ? "Export" : "Deletion"}
                      </TableCell>
                      <TableCell>
                        <Badge className={`text-[10px] ${STATUS_COLORS[req.status] ?? ""}`}>
                          {req.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(req.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        {req.status === "pending" && (
                          <div className="flex gap-1 justify-end">
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs"
                              onClick={() =>
                                reviewRequest.mutate({
                                  requestId: req.id,
                                  data: { action: "approve" },
                                })
                              }
                              disabled={reviewRequest.isPending}
                            >
                              <CheckCircle2 className="size-3 mr-1" />
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs text-danger"
                              onClick={() =>
                                reviewRequest.mutate({
                                  requestId: req.id,
                                  data: { action: "reject", note: "Rejected by admin" },
                                })
                              }
                              disabled={reviewRequest.isPending}
                            >
                              Reject
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request Data Deletion</DialogTitle>
            <DialogDescription>
              This will submit a request to delete your personal data. An admin must
              approve the request before processing. Your name, email, and phone will
              be anonymized, but structural data (task history, matter records) will
              be retained for audit integrity.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowDeleteConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeletionRequest}
              disabled={createRequest.isPending}
            >
              {createRequest.isPending ? (
                <Loader2 className="size-4 animate-spin mr-2" />
              ) : (
                <Trash2 className="size-4 mr-2" />
              )}
              Submit Deletion Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
