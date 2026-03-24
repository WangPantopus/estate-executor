import { describe, expect, it } from "vitest";

import { sanitizeSnippet } from "@/lib/utils";

describe("sanitizeSnippet", () => {
  it("preserves plain text", () => {
    expect(sanitizeSnippet("hello world")).toBe("hello world");
  });

  it("preserves safe <mark> tags", () => {
    expect(sanitizeSnippet("hello <mark>world</mark>")).toBe(
      "hello <mark>world</mark>"
    );
  });

  it("strips script tags", () => {
    const input = '<script>alert("xss")</script>';
    const result = sanitizeSnippet(input);
    expect(result).not.toContain("<script>");
    expect(result).not.toContain("</script>");
  });

  it("escapes img onerror payloads", () => {
    const input = '<img src=x onerror=alert(1)>';
    const result = sanitizeSnippet(input);
    // Should be fully escaped, no executable HTML
    expect(result).not.toContain("<img");
    expect(result).toContain("&lt;img");
  });

  it("escapes anchor tags", () => {
    const input = '<a href="javascript:alert(1)">click</a>';
    const result = sanitizeSnippet(input);
    // All tags escaped, not executable
    expect(result).not.toContain("<a");
    expect(result).toContain("&lt;a");
  });

  it("handles nested tags inside mark", () => {
    const input = "<mark><script>alert(1)</script></mark>";
    const result = sanitizeSnippet(input);
    expect(result).toContain("<mark>");
    expect(result).toContain("</mark>");
    expect(result).not.toContain("<script>");
  });

  it("escapes HTML entities correctly", () => {
    const input = '"><script>alert(1)</script>';
    const result = sanitizeSnippet(input);
    expect(result).toContain("&quot;");
    expect(result).toContain("&gt;");
    expect(result).not.toContain("<script>");
  });

  it("handles mark tags case-insensitively", () => {
    expect(sanitizeSnippet("<MARK>test</MARK>")).toBe("<mark>test</mark>");
  });

  it("handles empty input", () => {
    expect(sanitizeSnippet("")).toBe("");
  });

  it("handles ampersands and special chars", () => {
    const input = "Tom & Jerry's <mark>estate</mark>";
    const result = sanitizeSnippet(input);
    expect(result).toContain("&amp;");
    expect(result).toContain("&#x27;");
    expect(result).toContain("<mark>estate</mark>");
  });
});
