"use client";

import { useState } from "react";
import {
  User,
  Mail,
  Lock,
  Bell,
  Loader2,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/layout/LoadingState";
import { useCurrentUser } from "@/hooks";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const { data: user, isLoading } = useCurrentUser();
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState("");

  if (isLoading) {
    return <LoadingState variant="detail" />;
  }

  if (!user) {
    return (
      <div className="py-12 text-center">
        <p className="text-danger">Failed to load profile.</p>
      </div>
    );
  }

  const initials = user.full_name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader title="Profile" />

      {/* Avatar + name */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-4 mb-6">
            <Avatar className="size-16">
              <AvatarFallback className="text-lg">{initials}</AvatarFallback>
            </Avatar>
            <div>
              <h2 className="text-lg font-medium text-foreground">{user.full_name}</h2>
              <p className="text-sm text-muted-foreground">{user.email}</p>
              <div className="flex gap-1.5 mt-1">
                {user.firm_memberships.map((fm) => (
                  <Badge key={fm.firm_id} variant="muted" className="text-[10px]">
                    {fm.firm_name} · {fm.firm_role}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          <Separator />

          {/* Name */}
          <div className="mt-6">
            <Label>
              <User className="size-3.5 inline mr-1" />
              Full Name
            </Label>
            {editingName ? (
              <div className="flex items-center gap-2 mt-1">
                <Input
                  value={nameValue}
                  onChange={(e) => setNameValue(e.target.value)}
                  className="max-w-sm"
                />
                <Button size="sm" onClick={() => setEditingName(false)}>
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditingName(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2 mt-1">
                <p className="text-sm text-foreground">{user.full_name}</p>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setNameValue(user.full_name);
                    setEditingName(true);
                  }}
                >
                  Edit
                </Button>
              </div>
            )}
          </div>

          <Separator className="my-6" />

          {/* Email */}
          <div>
            <Label>
              <Mail className="size-3.5 inline mr-1" />
              Email
            </Label>
            <p className="text-sm text-foreground mt-1">{user.email}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Email changes are managed through your identity provider.
            </p>
          </div>

          <Separator className="my-6" />

          {/* Password */}
          <div>
            <Label>
              <Lock className="size-3.5 inline mr-1" />
              Password
            </Label>
            <p className="text-xs text-muted-foreground mt-1">
              Password is managed through Auth0.
            </p>
            <Button variant="outline" size="sm" className="mt-2" asChild>
              <a href="/api/auth/login?screen_hint=change-password" target="_blank" rel="noopener">
                Change Password
                <ExternalLink className="size-3 ml-1" />
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Notification preferences */}
      <Card>
        <CardContent className="p-6">
          <h3 className="text-sm font-medium text-foreground mb-1">
            <Bell className="size-3.5 inline mr-1" />
            Notification Preferences
          </h3>
          <p className="text-xs text-muted-foreground mb-4">
            Global defaults. Can be overridden per-matter in stakeholder settings.
          </p>

          <div className="space-y-3">
            {[
              { key: "task_assigned", label: "Task assigned to me" },
              { key: "task_overdue", label: "Task overdue" },
              { key: "deadline_approaching", label: "Deadline approaching" },
              { key: "document_uploaded", label: "Document uploaded" },
              { key: "comment_posted", label: "Comment posted" },
              { key: "milestone_reached", label: "Milestone reached" },
            ].map(({ key, label }) => (
              <label key={key} className="flex items-center justify-between">
                <span className="text-sm text-foreground">{label}</span>
                <input
                  type="checkbox"
                  defaultChecked
                  className="size-4 rounded border-border text-primary focus:ring-primary/40"
                />
              </label>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
