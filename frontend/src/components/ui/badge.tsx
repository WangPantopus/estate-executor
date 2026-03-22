import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "border-border text-foreground",
        success: "border-transparent bg-success-light text-success",
        warning: "border-transparent bg-warning-light text-warning",
        danger: "border-transparent bg-danger-light text-danger",
        info: "border-transparent bg-info-light text-info",
        gold: "border-transparent bg-[#F9F3E3] text-[#8B7335]",
        muted: "border-transparent bg-surface-elevated text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof badgeVariants>) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
