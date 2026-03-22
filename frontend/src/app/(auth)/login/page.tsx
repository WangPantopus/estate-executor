import { redirect } from "next/navigation";

/**
 * Login page — redirects to Auth0 Universal Login.
 *
 * In the SPA + API architecture, Auth0 handles the actual login UI.
 * This page simply redirects users to the Auth0 login route.
 */
export default function LoginPage() {
  redirect("/auth/login");
}
