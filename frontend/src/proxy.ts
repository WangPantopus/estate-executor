import { auth0 } from "@/lib/auth0";
import { NextResponse } from "next/server";

/**
 * Public routes that do not require authentication.
 */
const PUBLIC_ROUTES = ["/", "/auth/login", "/auth/signup", "/auth/callback"];

function isPublicRoute(pathname: string): boolean {
  if (PUBLIC_ROUTES.includes(pathname)) return true;
  // /invite/[token] is public (stakeholders need to sign up first)
  if (pathname.startsWith("/invite/")) return true;
  // Auth0 SDK routes
  if (pathname.startsWith("/auth/")) return true;
  return false;
}

export async function proxy(request: Request) {
  // Let Auth0 SDK handle its own routes (/auth/login, /auth/callback, etc.)
  const authResponse = await auth0.middleware(request);

  // For Auth0-handled routes, return the Auth0 response directly
  const url = new URL(request.url);
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
