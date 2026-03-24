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
  // First, escape all HTML entities to neutralize any malicious content
  const escaped = html
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");

  // Then restore only safe <mark> tags (no attributes allowed)
  return escaped
    .replace(/&lt;mark&gt;/gi, "<mark>")
    .replace(/&lt;\/mark&gt;/gi, "</mark>");
}
