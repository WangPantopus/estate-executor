import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Sanitize an HTML snippet to only allow safe `<mark>` tags.
 * Strips all other HTML to prevent XSS from user-supplied content
 * rendered via dangerouslySetInnerHTML (e.g., search result snippets).
 */
export function sanitizeSnippet(html: string): string {
  // Replace <mark> and </mark> with placeholders, strip all other tags, restore
  return html
    .replace(/<mark>/gi, "\x00MARK_OPEN\x00")
    .replace(/<\/mark>/gi, "\x00MARK_CLOSE\x00")
    .replace(/<[^>]*>/g, "")
    .replace(/\x00MARK_OPEN\x00/g, "<mark>")
    .replace(/\x00MARK_CLOSE\x00/g, "</mark>");
}
