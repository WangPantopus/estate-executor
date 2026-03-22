"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { EmptyState } from "@/components/layout/EmptyState";
import { LoadingState } from "@/components/layout/LoadingState";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  Plus,
  Download,
  Search,
  FileText,
  Briefcase,
  ArrowRight,
} from "lucide-react";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="py-8">
      <h2 className="text-xl font-medium text-foreground mb-6 pb-2 border-b border-border">
        {title}
      </h2>
      {children}
    </section>
  );
}

function ColorSwatch({
  name,
  value,
  textColor = "text-foreground",
}: {
  name: string;
  value: string;
  textColor?: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="size-12 rounded-lg border border-border shadow-xs shrink-0"
        style={{ backgroundColor: value }}
      />
      <div>
        <p className={`text-sm font-medium ${textColor}`}>{name}</p>
        <p className="text-xs text-muted-foreground">{value}</p>
      </div>
    </div>
  );
}

export default function StyleGuidePage() {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-primary text-primary-foreground py-16 px-6">
        <div className="mx-auto max-w-7xl">
          <p className="text-xs font-medium uppercase tracking-widest text-gold mb-3">
            Design System
          </p>
          <h1 className="text-4xl font-serif font-medium tracking-tight">
            Estate Executor OS
          </h1>
          <p className="mt-3 text-lg text-primary-foreground/70 max-w-2xl">
            A premium design system for estate administration. Clean, confident,
            spacious — inspired by private banking portals and modern SaaS.
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 pb-16">
        {/* ─── Colors ─── */}
        <Section title="Color Palette">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
            <ColorSwatch name="Primary (Deep Navy)" value="#0B1D3A" />
            <ColorSwatch name="Primary Light" value="#1A3A5C" />
            <ColorSwatch name="Accent (Warm Gold)" value="#C9A962" />
            <ColorSwatch name="Gold Light" value="#D4BC82" />
            <ColorSwatch name="Background" value="#FAFAF8" />
            <ColorSwatch name="Surface" value="#FFFFFF" />
            <ColorSwatch name="Surface Elevated" value="#F5F4F0" />
            <ColorSwatch name="Text Primary" value="#1A1A1A" />
            <ColorSwatch name="Text Secondary" value="#6B7280" />
            <ColorSwatch name="Text Muted" value="#9CA3AF" />
            <ColorSwatch name="Border" value="#E8E6E1" />
            <ColorSwatch name="Success" value="#2D6A4F" />
            <ColorSwatch name="Warning" value="#D4A843" />
            <ColorSwatch name="Danger" value="#9B2C2C" />
            <ColorSwatch name="Info" value="#4A6FA5" />
          </div>
        </Section>

        {/* ─── Typography ─── */}
        <Section title="Typography">
          <div className="space-y-8">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-4">
                Sans-Serif (Inter) — UI Text
              </p>
              <div className="space-y-4">
                <p className="text-3xl font-medium tracking-tight">
                  Heading 1 — 30px / Medium
                </p>
                <p className="text-2xl font-medium tracking-tight">
                  Heading 2 — 24px / Medium
                </p>
                <p className="text-xl font-medium">
                  Heading 3 — 20px / Medium
                </p>
                <p className="text-lg font-medium">
                  Heading 4 — 18px / Medium
                </p>
                <p className="text-base">
                  Body text — 16px / Regular. Estate administration is a
                  complex, multi-party process requiring coordination across
                  legal, financial, and family stakeholders.
                </p>
                <p className="text-sm text-muted-foreground">
                  Small text — 14px / Regular. Used for secondary information,
                  labels, and metadata.
                </p>
                <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
                  Caption / Overline — 12px / Medium / Uppercase
                </p>
              </div>
            </div>
            <Separator />
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-4">
                Serif (Crimson Pro) — Marketing & Portal Headings
              </p>
              <div className="space-y-4">
                <p className="text-3xl font-serif font-medium tracking-tight">
                  Estate of Jonathan Whitmore III
                </p>
                <p className="text-2xl font-serif font-medium tracking-tight">
                  Trust Administration Dashboard
                </p>
                <p className="text-xl font-serif font-medium">
                  Asset Distribution Summary
                </p>
              </div>
            </div>
          </div>
        </Section>

        {/* ─── Buttons ─── */}
        <Section title="Buttons">
          <div className="space-y-6">
            <div>
              <p className="text-sm text-muted-foreground mb-3">Variants</p>
              <div className="flex flex-wrap items-center gap-3">
                <Button>Primary</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="destructive">Destructive</Button>
                <Button variant="gold">Gold Accent</Button>
                <Button variant="link">Link</Button>
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-3">Sizes</p>
              <div className="flex flex-wrap items-center gap-3">
                <Button size="sm">Small</Button>
                <Button size="default">Default</Button>
                <Button size="lg">Large</Button>
                <Button size="icon">
                  <Plus />
                </Button>
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-3">With Icons</p>
              <div className="flex flex-wrap items-center gap-3">
                <Button>
                  <Plus /> New Matter
                </Button>
                <Button variant="outline">
                  <Download /> Export
                </Button>
                <Button variant="secondary">
                  <Search /> Search
                </Button>
                <Button disabled>Disabled</Button>
              </div>
            </div>
          </div>
        </Section>

        {/* ─── Cards ─── */}
        <Section title="Cards">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Estate of John Smith</CardTitle>
                <CardDescription>
                  Testate probate — California jurisdiction
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Tasks</p>
                    <p className="text-lg font-medium">24/48</p>
                  </div>
                  <Separator orientation="vertical" className="h-8" />
                  <div>
                    <p className="text-muted-foreground">Est. Value</p>
                    <p className="text-lg font-medium">$4.2M</p>
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <StatusBadge status="active" />
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Estate of Margaret Chen</CardTitle>
                <CardDescription>
                  Trust administration — New York jurisdiction
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Tasks</p>
                    <p className="text-lg font-medium">42/42</p>
                  </div>
                  <Separator orientation="vertical" className="h-8" />
                  <div>
                    <p className="text-muted-foreground">Est. Value</p>
                    <p className="text-lg font-medium">$8.7M</p>
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <StatusBadge status="closed" />
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Estate of Robert Williams</CardTitle>
                <CardDescription>
                  Mixed probate/trust — Texas jurisdiction
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Tasks</p>
                    <p className="text-lg font-medium">8/36</p>
                  </div>
                  <Separator orientation="vertical" className="h-8" />
                  <div>
                    <p className="text-muted-foreground">Est. Value</p>
                    <p className="text-lg font-medium">$12.1M</p>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="gap-2">
                <StatusBadge status="active" />
                <Badge variant="danger">2 overdue</Badge>
              </CardFooter>
            </Card>
          </div>
        </Section>

        {/* ─── Form Elements ─── */}
        <Section title="Form Elements">
          <Card className="max-w-lg">
            <CardContent className="pt-6 space-y-5">
              <div className="space-y-2">
                <Label htmlFor="name">Decedent Name</Label>
                <Input id="name" placeholder="Enter full legal name" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="jurisdiction">Jurisdiction</Label>
                <Select>
                  <SelectTrigger>
                    <SelectValue placeholder="Select state" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CA">California</SelectItem>
                    <SelectItem value="NY">New York</SelectItem>
                    <SelectItem value="TX">Texas</SelectItem>
                    <SelectItem value="FL">Florida</SelectItem>
                    <SelectItem value="IL">Illinois</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  placeholder="Additional details about the estate..."
                  rows={3}
                />
              </div>
              <div className="flex gap-3 pt-2">
                <Button>Create Matter</Button>
                <Button variant="outline">Cancel</Button>
              </div>
            </CardContent>
          </Card>
        </Section>

        {/* ─── Table ─── */}
        <Section title="Table">
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task</TableHead>
                  <TableHead>Phase</TableHead>
                  <TableHead>Assignee</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium">
                    Obtain death certificates (10 copies)
                  </TableCell>
                  <TableCell>Immediate</TableCell>
                  <TableCell>Jane Smith</TableCell>
                  <TableCell>Mar 28, 2026</TableCell>
                  <TableCell>
                    <StatusBadge status="complete" />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">
                    File petition for probate
                  </TableCell>
                  <TableCell>Probate Filing</TableCell>
                  <TableCell>Jane Smith</TableCell>
                  <TableCell>Apr 15, 2026</TableCell>
                  <TableCell>
                    <StatusBadge status="in_progress" />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">
                    Notify financial institutions
                  </TableCell>
                  <TableCell>Notification</TableCell>
                  <TableCell>Michael Torres</TableCell>
                  <TableCell>Apr 30, 2026</TableCell>
                  <TableCell>
                    <StatusBadge status="blocked" />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">
                    File federal estate tax return (Form 706)
                  </TableCell>
                  <TableCell>Tax</TableCell>
                  <TableCell>Sarah Park, CPA</TableCell>
                  <TableCell>Dec 22, 2026</TableCell>
                  <TableCell>
                    <StatusBadge status="not_started" />
                  </TableCell>
                </TableRow>
                <TableRow className="bg-danger-light/30">
                  <TableCell className="font-medium">
                    Publish creditor notice
                  </TableCell>
                  <TableCell>Notification</TableCell>
                  <TableCell>Jane Smith</TableCell>
                  <TableCell className="text-danger font-medium">
                    Mar 15, 2026
                  </TableCell>
                  <TableCell>
                    <StatusBadge status="overdue" />
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </Section>

        {/* ─── Badges & Status ─── */}
        <Section title="Badges & Status Indicators">
          <div className="space-y-6">
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Badge Variants
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge>Default</Badge>
                <Badge variant="secondary">Secondary</Badge>
                <Badge variant="outline">Outline</Badge>
                <Badge variant="success">Success</Badge>
                <Badge variant="warning">Warning</Badge>
                <Badge variant="danger">Danger</Badge>
                <Badge variant="info">Info</Badge>
                <Badge variant="gold">Gold</Badge>
                <Badge variant="muted">Muted</Badge>
              </div>
            </div>
            <Separator />
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Task Statuses
              </p>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status="not_started" />
                <StatusBadge status="in_progress" />
                <StatusBadge status="blocked" />
                <StatusBadge status="complete" />
                <StatusBadge status="waived" />
                <StatusBadge status="cancelled" />
                <StatusBadge status="overdue" />
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Asset Statuses
              </p>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status="discovered" />
                <StatusBadge status="valued" />
                <StatusBadge status="transferred" />
                <StatusBadge status="distributed" />
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Deadline Statuses
              </p>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status="upcoming" />
                <StatusBadge status="completed" />
                <StatusBadge status="extended" />
                <StatusBadge status="missed" />
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Matter Statuses
              </p>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status="active" />
                <StatusBadge status="on_hold" />
                <StatusBadge status="closed" />
                <StatusBadge status="archived" />
              </div>
            </div>
          </div>
        </Section>

        {/* ─── Avatars ─── */}
        <Section title="Avatars">
          <div className="flex items-center gap-4">
            <Avatar className="size-8">
              <AvatarFallback className="text-xs">JS</AvatarFallback>
            </Avatar>
            <Avatar>
              <AvatarFallback>MT</AvatarFallback>
            </Avatar>
            <Avatar className="size-12">
              <AvatarFallback className="text-base">SP</AvatarFallback>
            </Avatar>
            <Avatar className="size-14">
              <AvatarImage src="" alt="User" />
              <AvatarFallback className="text-lg bg-gold text-primary">
                RW
              </AvatarFallback>
            </Avatar>
          </div>
        </Section>

        {/* ─── Tabs ─── */}
        <Section title="Tabs">
          <Tabs defaultValue="overview">
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="tasks">Tasks</TabsTrigger>
              <TabsTrigger value="documents">Documents</TabsTrigger>
              <TabsTrigger value="activity">Activity</TabsTrigger>
            </TabsList>
            <TabsContent value="overview">
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">
                    Matter overview with key metrics, recent activity, and
                    upcoming deadlines.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="tasks">
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">
                    Task list with filters by phase, status, and assignee.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="documents">
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">
                    Document management with upload, classification, and
                    versioning.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="activity">
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">
                    Immutable activity log showing all matter events.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </Section>

        {/* ─── Dialog ─── */}
        <Section title="Dialog">
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>Open Dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Matter</DialogTitle>
                <DialogDescription>
                  Begin a new estate administration case. You&apos;ll be able to
                  configure details after creation.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="dialog-name">Decedent Name</Label>
                  <Input id="dialog-name" placeholder="Enter full legal name" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dialog-type">Estate Type</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="testate_probate">
                        Testate Probate
                      </SelectItem>
                      <SelectItem value="intestate_probate">
                        Intestate Probate
                      </SelectItem>
                      <SelectItem value="trust_administration">
                        Trust Administration
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={() => setDialogOpen(false)}>
                  Create Matter
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </Section>

        {/* ─── Page Header ─── */}
        <Section title="Page Header">
          <div className="space-y-8">
            <div className="rounded-lg border border-border bg-card p-6">
              <PageHeader
                title="Matters"
                subtitle="Manage all active and archived estate matters"
                actions={
                  <Button>
                    <Plus /> New Matter
                  </Button>
                }
              />
            </div>
            <div className="rounded-lg border border-border bg-card p-6">
              <PageHeader
                title="Estate of John Smith"
                subtitle="Testate probate — California"
                serif
                actions={
                  <>
                    <Button variant="outline">
                      <Download /> Export
                    </Button>
                    <Button>
                      <ArrowRight /> Next Phase
                    </Button>
                  </>
                }
              />
            </div>
          </div>
        </Section>

        {/* ─── Empty States ─── */}
        <Section title="Empty States">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <EmptyState
                title="No matters yet"
                description="Create your first estate matter to begin tracking tasks, assets, and deadlines."
                action={
                  <Button>
                    <Plus /> Create Matter
                  </Button>
                }
              />
            </Card>
            <Card>
              <EmptyState
                icon={<FileText className="size-12" />}
                title="No documents uploaded"
                description="Upload estate documents to enable AI classification and data extraction."
                action={<Button variant="outline">Upload Document</Button>}
              />
            </Card>
          </div>
        </Section>

        {/* ─── Loading States ─── */}
        <Section title="Loading States">
          <div className="space-y-8">
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Cards Skeleton
              </p>
              <LoadingState variant="cards" count={3} />
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Table Skeleton
              </p>
              <LoadingState variant="table" count={4} />
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Detail Skeleton
              </p>
              <LoadingState variant="detail" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                List Skeleton
              </p>
              <LoadingState variant="list" count={3} />
            </div>
          </div>
        </Section>

        {/* ─── Shadows ─── */}
        <Section title="Shadows & Elevation">
          <div className="flex flex-wrap gap-6">
            {(["shadow-xs", "shadow-sm", "shadow-md", "shadow-lg", "shadow-xl"] as const).map(
              (shadow) => (
                <div
                  key={shadow}
                  className={`${shadow} rounded-lg border border-border bg-card px-8 py-6`}
                >
                  <p className="text-sm font-medium">{shadow}</p>
                </div>
              )
            )}
          </div>
        </Section>

        {/* ─── Spacing & Layout ─── */}
        <Section title="Spacing & Layout Principles">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4 text-sm">
                <div className="flex items-baseline gap-4">
                  <span className="font-medium w-40 shrink-0">Card Padding</span>
                  <span className="text-muted-foreground">
                    px-6 py-5 minimum — generous internal spacing
                  </span>
                </div>
                <Separator />
                <div className="flex items-baseline gap-4">
                  <span className="font-medium w-40 shrink-0">Section Gap</span>
                  <span className="text-muted-foreground">
                    py-8 minimum between major sections
                  </span>
                </div>
                <Separator />
                <div className="flex items-baseline gap-4">
                  <span className="font-medium w-40 shrink-0">Page Container</span>
                  <span className="text-muted-foreground">
                    max-w-7xl with px-6 side padding
                  </span>
                </div>
                <Separator />
                <div className="flex items-baseline gap-4">
                  <span className="font-medium w-40 shrink-0">Border Radius</span>
                  <span className="text-muted-foreground">
                    rounded-lg (8px) for cards, rounded-md (6px) for inputs
                  </span>
                </div>
                <Separator />
                <div className="flex items-baseline gap-4">
                  <span className="font-medium w-40 shrink-0">Animations</span>
                  <span className="text-muted-foreground">
                    200ms ease-out — subtle and smooth, never bouncy
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </Section>
      </div>
    </div>
  );
}
