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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
} from "@/hooks";
import type { FirmRole } from "@/lib/types";

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
          <div className="space-y-4">
            {/* Current plan */}
            <Card>
              <CardContent className="p-6">
                <h3 className="text-sm font-medium text-foreground mb-4">Current Plan</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xl font-semibold text-foreground">{tierInfo.name}</p>
                    <p className="text-sm text-muted-foreground">{tierInfo.price}</p>
                  </div>
                  <Button variant="outline" size="sm" disabled>
                    Upgrade Plan
                  </Button>
                </div>

                <Separator className="my-4" />

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Matters</p>
                    <p className="text-sm text-foreground">
                      — / {tierInfo.matters}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Team Members</p>
                    <p className="text-sm text-foreground">
                      {members.length} / {tierInfo.users}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Billing history placeholder */}
            <Card>
              <CardContent className="p-6">
                <h3 className="text-sm font-medium text-foreground mb-4">Billing History</h3>
                <p className="text-sm text-muted-foreground">No invoices yet.</p>
              </CardContent>
            </Card>
          </div>
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
