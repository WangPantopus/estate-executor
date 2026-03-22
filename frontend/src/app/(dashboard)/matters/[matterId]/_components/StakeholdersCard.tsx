import Link from "next/link";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/layout/StatusBadge";
import type { Stakeholder } from "@/lib/types";

const ROLE_LABELS: Record<string, string> = {
  matter_admin: "Admin",
  professional: "Professional",
  executor_trustee: "Executor",
  beneficiary: "Beneficiary",
  read_only: "Read Only",
};

interface StakeholdersCardProps {
  stakeholders: Stakeholder[];
  matterId: string;
}

export function StakeholdersCard({
  stakeholders,
  matterId,
}: StakeholdersCardProps) {
  const display = stakeholders.slice(0, 5);
  const remaining = stakeholders.length - 5;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Stakeholders</CardTitle>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/matters/${matterId}/stakeholders`}>View all</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 pt-0">
        {display.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-2">
            No stakeholders yet.
          </p>
        ) : (
          display.map((s) => (
            <div
              key={s.id}
              className="flex items-center gap-3 rounded-md px-2 py-1.5"
            >
              <Avatar className="size-8">
                <AvatarFallback className="text-xs">
                  {s.full_name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")
                    .toUpperCase()
                    .slice(0, 2)}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{s.full_name}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {s.email}
                </p>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <Badge variant="secondary" className="text-[10px]">
                  {ROLE_LABELS[s.role] ?? s.role}
                </Badge>
                {s.invite_status === "pending" && (
                  <StatusBadge status="pending" />
                )}
              </div>
            </div>
          ))
        )}
        {remaining > 0 && (
          <p className="text-xs text-muted-foreground text-center pt-1">
            +{remaining} more
          </p>
        )}
      </CardContent>
    </Card>
  );
}
