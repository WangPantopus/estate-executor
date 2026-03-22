"use client";

import {
  Home,
  Landmark,
  TrendingUp,
  PiggyBank,
  Shield,
  Briefcase,
  Car,
  Globe,
  Package,
  Receipt,
  HelpCircle,
  Paperclip,
  Link2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/layout/StatusBadge";
import {
  ASSET_TYPE_LABELS,
  OWNERSHIP_TYPE_LABELS,
  TRANSFER_MECHANISM_LABELS,
} from "@/lib/constants";
import type { AssetListItem, AssetType } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Icon mapping ─────────────────────────────────────────────────────────────

const ASSET_TYPE_ICONS: Record<AssetType, React.ReactNode> = {
  real_estate: <Home className="size-5" />,
  bank_account: <Landmark className="size-5" />,
  brokerage_account: <TrendingUp className="size-5" />,
  retirement_account: <PiggyBank className="size-5" />,
  life_insurance: <Shield className="size-5" />,
  business_interest: <Briefcase className="size-5" />,
  vehicle: <Car className="size-5" />,
  digital_asset: <Globe className="size-5" />,
  personal_property: <Package className="size-5" />,
  receivable: <Receipt className="size-5" />,
  other: <HelpCircle className="size-5" />,
};

const ASSET_TYPE_COLORS: Record<AssetType, string> = {
  real_estate: "text-emerald-600 bg-emerald-50",
  bank_account: "text-blue-600 bg-blue-50",
  brokerage_account: "text-violet-600 bg-violet-50",
  retirement_account: "text-amber-600 bg-amber-50",
  life_insurance: "text-cyan-600 bg-cyan-50",
  business_interest: "text-slate-600 bg-slate-100",
  vehicle: "text-orange-600 bg-orange-50",
  digital_asset: "text-indigo-600 bg-indigo-50",
  personal_property: "text-rose-600 bg-rose-50",
  receivable: "text-teal-600 bg-teal-50",
  other: "text-gray-500 bg-gray-100",
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

// ─── Component ────────────────────────────────────────────────────────────────

interface AssetCardProps {
  asset: AssetListItem;
  onClick: () => void;
}

export function AssetCard({ asset, onClick }: AssetCardProps) {
  const displayValue =
    asset.current_estimated_value ?? asset.date_of_death_value ?? null;
  const entityName = asset.entities.length > 0 ? asset.entities[0].name : null;

  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30 group"
      onClick={onClick}
    >
      <CardContent className="p-4">
        {/* Top row: icon + type + status */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div
              className={cn(
                "flex items-center justify-center size-9 rounded-lg shrink-0",
                ASSET_TYPE_COLORS[asset.asset_type],
              )}
            >
              {ASSET_TYPE_ICONS[asset.asset_type]}
            </div>
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">
                {ASSET_TYPE_LABELS[asset.asset_type]}
              </p>
              <h3 className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
                {asset.title}
              </h3>
            </div>
          </div>
          <StatusBadge status={asset.status} />
        </div>

        {/* Institution */}
        {asset.institution && (
          <p className="text-xs text-muted-foreground mb-2 truncate">
            {asset.institution}
            {asset.account_number_masked && (
              <span className="ml-1.5 font-mono">{asset.account_number_masked}</span>
            )}
          </p>
        )}

        {/* Value */}
        {displayValue !== null && (
          <p className="text-lg font-semibold text-foreground tabular-nums mb-2">
            {formatCurrency(displayValue)}
          </p>
        )}
        {displayValue === null && (
          <p className="text-sm text-muted-foreground italic mb-2">No valuation</p>
        )}

        {/* Badges row */}
        <div className="flex flex-wrap gap-1.5 mb-2">
          {asset.ownership_type && (
            <Badge variant="outline" className="text-[10px]">
              {OWNERSHIP_TYPE_LABELS[asset.ownership_type]}
            </Badge>
          )}
          {asset.transfer_mechanism && (
            <Badge variant="muted" className="text-[10px]">
              {TRANSFER_MECHANISM_LABELS[asset.transfer_mechanism]}
            </Badge>
          )}
        </div>

        {/* Footer: entity + docs */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border">
          {entityName ? (
            <span className="inline-flex items-center gap-1 truncate max-w-[60%]">
              <Link2 className="size-3 shrink-0" />
              {entityName}
            </span>
          ) : (
            <span>No linked entity</span>
          )}
          {asset.document_count > 0 && (
            <span className="inline-flex items-center gap-0.5 shrink-0">
              <Paperclip className="size-3" />
              {asset.document_count}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Re-export for use in other components
export { ASSET_TYPE_ICONS, ASSET_TYPE_COLORS };
