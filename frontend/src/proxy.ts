import { auth0 } from "@/lib/auth0";
import { NextResponse } from "next/server";

/**
 * Public routes that do not require authentication.
 */
const PUBLIC_ROUTES = ["/", "/auth/login", "/auth/signup", "/auth/callback"];

const isMockAuth = process.env.E2E_MOCK_AUTH === "true";

function isPublicRoute(pathname: string): boolean {
  if (PUBLIC_ROUTES.includes(pathname)) return true;
  // /invite/[token] is public (stakeholders need to sign up first)
  if (pathname.startsWith("/invite/")) return true;
  // Auth0 SDK routes
  if (pathname.startsWith("/auth/")) return true;
  return false;
}

/**
 * Parse the mock appSession cookie to extract the user key.
 */
function getMockUserKey(request: Request): string | null {
  const cookieHeader = request.headers.get("cookie") ?? "";
  const match = cookieHeader.match(/appSession=([^;]+)/);
  if (!match) return null;
  try {
    const decoded = decodeURIComponent(match[1]);
    const session = JSON.parse(decoded);
    // sub is "auth0|e2e-admin" → extract "admin"
    const sub: string = session?.user?.sub ?? "";
    const key = sub.replace("auth0|e2e-", "");
    return key || null;
  } catch {
    return null;
  }
}

export async function proxy(request: Request) {
  const url = new URL(request.url);

  // --- E2E mock auth bypass ---
  if (isMockAuth) {
    const userKey = getMockUserKey(request);

    // Serve /auth/token with mock token when user has a mock session
    if (url.pathname === "/auth/token" && userKey) {
      return NextResponse.json({ accessToken: `e2e-mock-token-${userKey}` });
    }

    // Handle /auth/logout in mock mode — clear cookie and redirect to /
    if (url.pathname === "/auth/logout") {
      const res = NextResponse.redirect(new URL("/login", request.url));
      res.cookies.delete("appSession");
      return res;
    }

    // For protected routes, skip Auth0 session check if mock cookie present
    if (userKey && !isPublicRoute(url.pathname)) {
      return NextResponse.next();
    }
  }

  // Let Auth0 SDK handle its own routes (/auth/login, /auth/callback, etc.)
  const authResponse = await auth0.middleware(request);

  // For Auth0-handled routes, return the Auth0 response directly
  if (url.pathname.startsWith("/auth/")) {
    return authResponse;
  }

  // For public routes, pass through
  if (isPublicRoute(url.pathname)) {
    return authResponse;
  }

  // For protected routes, check if user has a session
  const session = await auth0.getSession();
  if (!session) {
    // Redirect to login, preserving the intended destination
    const loginUrl = new URL("/auth/login", request.url);
    loginUrl.searchParams.set("returnTo", url.pathname + url.search);
    return NextResponse.redirect(loginUrl);
  }

  return authResponse;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
