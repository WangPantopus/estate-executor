import { redirect } from "next/navigation";

/**
 * Signup page — redirects to Auth0 Universal Login with signup screen hint.
 */
export default function SignupPage() {
  redirect("/auth/login?screen_hint=signup");
}
