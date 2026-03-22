import type { EventResponse } from "@/lib/types";

/**
 * Generates a human-readable description from an Event object.
 * Handles all entity_type + action combinations.
 */
export function describeEvent(event: EventResponse): string {
  const rawActor = event.actor_name ?? event.actor_type;
  const actor = rawActor === "system" ? "System" : rawActor === "ai" ? "AI" : rawActor;
  const meta = event.metadata ?? {};
  const changes = event.changes ?? {};

  // Helper to extract a title from metadata or changes
  const title = (meta.title as string) ?? (meta.filename as string) ?? (meta.name as string) ?? "";

  switch (event.entity_type) {
    case "task":
      return describeTaskEvent(actor, event.action, title, meta, changes);
    case "asset":
      return describeAssetEvent(actor, event.action, title, meta, changes);
    case "document":
      return describeDocumentEvent(actor, event.action, title, meta, changes);
    case "stakeholder":
      return describeStakeholderEvent(actor, event.action, meta);
    case "matter":
      return describeMatterEvent(actor, event.action, meta, changes);
    case "deadline":
      return describeDeadlineEvent(actor, event.action, title, changes);
    case "communication":
      return describeCommunicationEvent(actor, event.action, meta);
    case "entity":
      return describeEntityEvent(actor, event.action, title, meta);
    default:
      return `${actor} ${event.action} ${event.entity_type}`;
  }
}

function describeTaskEvent(
  actor: string,
  action: string,
  title: string,
  meta: Record<string, unknown>,
  changes: Record<string, unknown>,
): string {
  const taskRef = title ? ` '${title}'` : "";
  switch (action) {
    case "created":
      return `${actor} created task${taskRef}`;
    case "updated": {
      const fields = Object.keys(changes);
      if (fields.includes("status")) {
        const to = (changes.status as { to?: string })?.to;
        if (to) return `${actor} changed task${taskRef} status to ${to.replace(/_/g, " ")}`;
      }
      if (fields.includes("assigned_to"))
        return `${actor} reassigned task${taskRef}`;
      return `${actor} updated task${taskRef}`;
    }
    case "completed":
      return `${actor} completed task${taskRef}`;
    case "waived":
      return `${actor} waived task${taskRef}`;
    case "assigned":
      return `${actor} assigned task${taskRef}`;
    case "generated": {
      const count = (meta.count as number) ?? "";
      return `${actor} generated ${count} tasks from template`;
    }
    default:
      return `${actor} ${action} task${taskRef}`;
  }
}

function describeAssetEvent(
  actor: string,
  action: string,
  title: string,
  meta: Record<string, unknown>,
  changes: Record<string, unknown>,
): string {
  const ref = title ? ` '${title}'` : "";
  switch (action) {
    case "created":
      return `${actor} added asset${ref}`;
    case "updated": {
      const fields = Object.keys(changes);
      if (fields.includes("status")) {
        const to = (changes.status as { to?: string })?.to;
        if (to) return `${actor} marked asset${ref} as ${to}`;
      }
      return `${actor} updated asset${ref}`;
    }
    case "valued":
      return `${actor} updated valuation for asset${ref}`;
    case "deleted":
      return `${actor} removed asset${ref}`;
    default:
      return `${actor} ${action} asset${ref}`;
  }
}

function describeDocumentEvent(
  actor: string,
  action: string,
  title: string,
  meta: Record<string, unknown>,
  changes: Record<string, unknown>,
): string {
  const ref = title ? ` '${title}'` : "";
  switch (action) {
    case "uploaded":
      return `${actor} uploaded document${ref}`;
    case "created":
      return `${actor} registered document${ref}`;
    case "classified": {
      const docType = (meta.doc_type as string) ?? "";
      const confidence = meta.confidence as number | undefined;
      const confStr = confidence ? ` (${Math.round(confidence * 100)}% confidence)` : "";
      return `${actor} classified document${ref} as ${docType.replace(/_/g, " ")}${confStr}`;
    }
    case "confirmed":
      return `${actor} confirmed classification of document${ref}`;
    case "versioned":
      return `${actor} uploaded new version of document${ref}`;
    default:
      return `${actor} ${action} document${ref}`;
  }
}

function describeStakeholderEvent(
  actor: string,
  action: string,
  meta: Record<string, unknown>,
): string {
  const name = (meta.full_name as string) ?? (meta.email as string) ?? "";
  const ref = name ? ` ${name}` : "";
  switch (action) {
    case "invited":
      return `${actor} invited${ref} as stakeholder`;
    case "accepted":
      return `${ref || "A stakeholder"} accepted their invitation`;
    case "removed":
      return `${actor} removed stakeholder${ref}`;
    case "updated":
      return `${actor} updated stakeholder${ref}`;
    default:
      return `${actor} ${action} stakeholder${ref}`;
  }
}

function describeMatterEvent(
  actor: string,
  action: string,
  meta: Record<string, unknown>,
  changes: Record<string, unknown>,
): string {
  switch (action) {
    case "created":
      return `${actor} created this matter`;
    case "updated": {
      const fields = Object.keys(changes);
      if (fields.includes("status")) {
        const to = (changes.status as { to?: string })?.to;
        if (to) return `${actor} changed matter status to ${to.replace(/_/g, " ")}`;
      }
      if (fields.includes("phase")) {
        const to = (changes.phase as { to?: string })?.to;
        if (to) return `${actor} advanced matter to ${to} phase`;
      }
      return `${actor} updated matter details`;
    }
    case "closed":
      return `${actor} closed this matter`;
    default:
      return `${actor} ${action} matter`;
  }
}

function describeDeadlineEvent(
  actor: string,
  action: string,
  title: string,
  changes: Record<string, unknown>,
): string {
  const ref = title ? ` '${title}'` : "";
  switch (action) {
    case "created":
      return `${actor} created deadline${ref}`;
    case "completed":
      return `${actor} marked deadline${ref} as completed`;
    case "extended":
      return `${actor} extended deadline${ref}`;
    case "missed":
      return `Deadline${ref} was missed`;
    case "updated":
      return `${actor} updated deadline${ref}`;
    default:
      return `${actor} ${action} deadline${ref}`;
  }
}

function describeCommunicationEvent(
  actor: string,
  action: string,
  meta: Record<string, unknown>,
): string {
  const commType = (meta.type as string) ?? "message";
  switch (action) {
    case "created":
      return `${actor} sent a ${commType.replace(/_/g, " ")}`;
    case "acknowledged":
      return `${actor} acknowledged a distribution notice`;
    default:
      return `${actor} ${action} communication`;
  }
}

function describeEntityEvent(
  actor: string,
  action: string,
  title: string,
  meta: Record<string, unknown>,
): string {
  const ref = title ? ` '${title}'` : "";
  switch (action) {
    case "created":
      return `${actor} created entity${ref}`;
    case "updated":
      return `${actor} updated entity${ref}`;
    case "deleted":
      return `${actor} deleted entity${ref}`;
    default:
      return `${actor} ${action} entity${ref}`;
  }
}

/**
 * Formats event changes as an array of { field, from, to } diffs.
 */
export function formatChanges(
  changes: Record<string, unknown> | null,
): { field: string; from: string; to: string }[] {
  if (!changes) return [];
  return Object.entries(changes).map(([key, value]) => {
    if (typeof value === "object" && value !== null && "from" in value && "to" in value) {
      const v = value as { from: unknown; to: unknown };
      return {
        field: key.replace(/_/g, " "),
        from: String(v.from ?? "—"),
        to: String(v.to ?? "—"),
      };
    }
    return {
      field: key.replace(/_/g, " "),
      from: "—",
      to: String(value ?? "—"),
    };
  });
}
