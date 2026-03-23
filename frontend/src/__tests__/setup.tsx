import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// ─── Mock Next.js modules ────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => "/matters",
  useParams: () => ({ matterId: "matter-1" }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => {
    return <a href={href} {...props}>{children}</a>; // eslint-disable-line @next/next/no-html-link-for-pages
  },
}));

// ─── Mock Auth0 ──────────────────────────────────────────────────────────────

vi.mock("@auth0/nextjs-auth0", () => ({
  Auth0Provider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useUser: () => ({
    user: { sub: "user-1", email: "test@example.com", name: "Test User" },
    isLoading: false,
    error: undefined,
  }),
}));

vi.mock("@/lib/auth", () => ({
  auth0: { getAccessToken: vi.fn().mockResolvedValue("mock-token") },
}));

vi.mock("@/lib/auth0", () => ({
  auth0: { getAccessToken: vi.fn().mockResolvedValue("mock-token") },
}));

// ─── Mock Socket.IO ──────────────────────────────────────────────────────────

vi.mock("socket.io-client", () => ({
  io: vi.fn(() => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    connect: vi.fn(),
    disconnect: vi.fn(),
    connected: false,
  })),
}));

vi.mock("@/hooks/use-matter-socket", () => ({
  useMatterSocket: () => ({ status: "connected" as const }),
}));

vi.mock("@/components/providers/SocketProvider", () => ({
  useSocket: () => ({
    status: "connected" as const,
    socket: null,
    joinMatter: vi.fn(),
    leaveMatter: vi.fn(),
  }),
  SocketProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ─── Mock IntersectionObserver (needed by Radix) ─────────────────────────────

class MockIntersectionObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
Object.defineProperty(window, "IntersectionObserver", {
  value: MockIntersectionObserver,
});

// ─── Mock ResizeObserver ─────────────────────────────────────────────────────

class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
Object.defineProperty(window, "ResizeObserver", {
  value: MockResizeObserver,
});

// ─── Mock matchMedia ─────────────────────────────────────────────────────────

Object.defineProperty(window, "matchMedia", {
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ─── Mock Radix ScrollArea (doesn't render children in jsdom) ────────────────

vi.mock("@/components/ui/scroll-area", () => ({
  ScrollArea: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
    <div data-testid="scroll-area" {...props}>{children}</div>
  ),
}));

// ─── Mock Radix Collapsible (content doesn't render in jsdom) ────────────────

vi.mock("@/components/ui/collapsible", () => ({
  Collapsible: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
    <div data-testid="collapsible" {...props}>{children}</div>
  ),
  CollapsibleTrigger: ({ children, asChild: _, ...props }: { children: React.ReactNode; asChild?: boolean; [key: string]: unknown }) => ( // eslint-disable-line @typescript-eslint/no-unused-vars
    <div data-testid="collapsible-trigger" {...props}>{children}</div>
  ),
  CollapsibleContent: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
    <div data-testid="collapsible-content" {...props}>{children}</div>
  ),
}));

// Suppress React act warnings in test output
const originalError = console.error;
console.error = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes("act(")) return;
  originalError(...args);
};
